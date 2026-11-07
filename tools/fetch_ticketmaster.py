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

CENTERS = {  # same city centers as the LaughsLive page (lat, lng)
 "NYC":(40.7549,-73.9840),"PHL":(39.9526,-75.1652),"BOS":(42.3601,-71.0589),"BAL":(39.2904,-76.6122),
 "DC":(38.9072,-77.0369),"PIT":(40.4406,-79.9959),"CLE":(41.4993,-81.6944),"NSH":(36.1627,-86.7816),
 "PWM":(43.6591,-70.2568),"CHI":(41.8781,-87.6298),"ATL":(33.7490,-84.3880),"RIC":(37.5407,-77.4360),
 "ORF":(36.8508,-76.2859),"HFD":(41.7658,-72.6734),"NHV":(41.3083,-72.9279),"MIA":(25.7617,-80.1918),
 "TPA":(27.9506,-82.4572),"ORL":(28.5384,-81.3789),"CIN":(39.1031,-84.5120),"STL":(38.6270,-90.1994),
 "MSP":(44.9778,-93.2650),"MKE":(43.0389,-87.9065),"DET":(42.3314,-83.0458),
 "DEN":(39.7392,-104.9903),"IND":(39.7684,-86.1581),"AUS":(30.2672,-97.7431),"DFW":(32.7767,-96.7970),
 "PHX":(33.4484,-112.0740),"LAS":(36.1147,-115.1728)}
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
