#!/usr/bin/env python3
"""Fetch upcoming stand-up comedy from Ticketmaster's Discovery API for LaughsLive's
29 cities and save a compact list to data/ticketmaster.json.

Runs in GitHub Actions (see .github/workflows/ticketmaster.yml). The API key comes
from the TM_API_KEY repository secret and is never written to the repository.
Only the "Comedy" genre is requested, so Broadway plays tagged as comedy are excluded.
"""
import datetime, json, os, sys, time, urllib.parse, urllib.request

KEY = os.environ.get("TM_API_KEY")
if not KEY:
    sys.exit("TM_API_KEY is not set")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CENTERS = {c["code"]: tuple(c["center"]) for c in
           json.load(open(os.path.join(_ROOT, "data", "cities.json"), encoding="utf-8"))["cities"]}
COMEDY_GENRE = "KnvZfZ7vAe1"   # Ticketmaster classification: Arts & Theatre > Comedy
DAYS_AHEAD = 70

def get(params):
    url = "https://app.ticketmaster.com/discovery/v2/events.json?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 + attempt * 2); continue
            raise
    raise RuntimeError("rate limited")

def main():
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    end = now + datetime.timedelta(days=DAYS_AHEAD)
    seen, out = set(), []
    for code, (lat, lng) in CENTERS.items():
        page, n = 0, 0
        while True:
            data = get({"apikey": KEY, "genreId": COMEDY_GENRE, "latlong": f"{lat},{lng}",
                        "radius": 50, "unit": "miles", "size": 200, "page": page, "sort": "date,asc",
                        "startDateTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "endDateTime": end.strftime("%Y-%m-%dT%H:%M:%SZ")})
            time.sleep(0.25)
            for e in data.get("_embedded", {}).get("events", []):
                st = e.get("dates", {}).get("start", {})
                if not st.get("localDate") or not st.get("localTime") or e["id"] in seen:
                    continue
                seen.add(e["id"]); n += 1
                v = (e.get("_embedded", {}).get("venues") or [{}])[0]
                loc = v.get("location") or {}
                pr = (e.get("priceRanges") or [{}])[0]
                cls = (e.get("classifications") or [{}])[0]
                out.append({
                    "city": code, "id": e["id"], "name": e.get("name"),
                    "date": st["localDate"], "time": st["localTime"][:5],
                    "status": e.get("dates", {}).get("status", {}).get("code"),
                    "venue": v.get("name"), "venueCity": (v.get("city") or {}).get("name"),
                    "state": (v.get("state") or {}).get("stateCode"), "address": (v.get("address") or {}).get("line1"),
                    "lat": float(loc["latitude"]) if loc.get("latitude") else None,
                    "lng": float(loc["longitude"]) if loc.get("longitude") else None,
                    "url": e.get("url"), "priceMin": pr.get("min"), "priceMax": pr.get("max"),
                    "subGenre": (cls.get("subGenre") or {}).get("name"),
                    "attractions": [a.get("name") for a in e.get("_embedded", {}).get("attractions", [])],
                    "ageRestricted": bool((e.get("ageRestrictions") or {}).get("legalAgeEnforced")),
                })
            pg = data.get("page", {})
            page += 1
            if page >= pg.get("totalPages", 0) or (page + 1) * 200 > 1000:
                break
        print(f"{code}: {n} events")
    out.sort(key=lambda x: (x["city"], x["date"], x["time"]))
    os.makedirs("data", exist_ok=True)
    with open("data/ticketmaster.json", "w") as f:
        json.dump({"fetched": now.isoformat(), "source": "Ticketmaster Discovery API", "events": out},
                  f, ensure_ascii=False, indent=0)
    print(f"total {len(out)} events")

if __name__ == "__main__":
    main()
