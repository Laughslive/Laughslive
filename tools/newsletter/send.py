"""Weekly LaughsLive newsletter: one email per city, sent through Brevo.

Runs from .github/workflows/newsletter.yml (Thursday, with Friday/Saturday catch-up runs).
- Reads subscribers of the Brevo list "LaughsLive Newsletter" and groups them by their CITY.
- For each city with subscribers: builds that city's email from the site's own listings
  (tools/newsletter/build_email.py), keeps a per-city Brevo list in sync, creates a campaign and sends it.
- Brevo's free plan allows 300 emails a day in total, so cities are sent biggest first until the day's
  budget is used; the rest go out on the next run. data/newsletter_state.json records which cities
  already got this week's email, so nothing is sent twice.

Environment: BREVO_API_KEY (GitHub secret). Optional: DAILY_LIMIT (default 290),
TEST_EMAIL + TEST_CITY (send one city's email as a Brevo test to that address only; nothing to subscribers),
DRY_RUN=1 (build only, print what would be sent).
"""
import datetime, json, os, subprocess, sys, tempfile, urllib.request, urllib.error

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))
from build_email import build, group, is_big, STARS  # noqa: E402

API = "https://api.brevo.com/v3"
MAIN_LIST = "LaughsLive Newsletter"
CITY_LIST_PREFIX = "Newsletter city: "
SENDER = {"name": "LaughsLive", "email": "info@laughslive.com"}
STATE = os.path.join(ROOT, "data", "newsletter_state.json")
CITIES = json.load(open(os.path.join(ROOT, "data", "cities.json")))["cities"]
BY_NAME = {c["name"].lower(): c for c in CITIES}


def api(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"api-key": os.environ["BREVO_API_KEY"], "accept": "application/json",
                                          "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            txt = r.read().decode()
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Brevo {method} {path} failed: {e.code} {e.read().decode()[:500]}")


def all_pages(path, key):
    out, off = [], 0
    while True:
        sep = "&" if "?" in path else "?"
        page = api("GET", f"{path}{sep}limit=50&offset={off}").get(key) or []
        out += page
        if len(page) < 50:
            return out
        off += 50


def week_window(today):
    """The email covers today (Thursday) through the following Wednesday."""
    start = today
    while start.weekday() != 3 and (today - start).days < 6:  # back up to this week's Thursday
        start -= datetime.timedelta(days=1)
    end = start + datetime.timedelta(days=6)
    return start, end


def shows_by_city(start, end):
    """Run the page's own data code in node (as build_pages.py does) and export each city's week."""
    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    import re
    src = re.sub(r"<!--ll:(\w+)-->.*?<!--/ll:\1-->\n?", "", src, flags=re.S)
    js = src[src.rindex("<script>") + len("<script>"): src.rindex("</script>")]
    js = js[: js.index("// Show the first PAGE shows")] if "// Show the first PAGE shows" in js else js[: js.index("function render")]
    js += r"""
const [S0,S1]=process.argv.slice(2);const out={};
for(const c in CENTER){
  out[c]=SHOWS.filter(s=>{const m=miles(CENTER[c],[s.v.lat,s.v.lng]);s._mi=m;return m<=RADIUS&&s.d>=S0&&s.d<=S1})
    .map(s=>{const l=ticketLink(s)||{};return {d:s.d,t:s.t,title:s.title,who:s.who,v:s.v.n,area:s.v.area,b:s.v.b,
      head:!!s.headliner,type:s.type,flags:s.flags,url:l.href||s.url,label:l.label,mi:+miles(CENTER[c],[s.v.lat,s.v.lng]).toFixed(1),price:s.price}});
}
console.log(JSON.stringify(out));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js)
        path = f.name
    try:
        return json.loads(subprocess.check_output(["node", path, start.isoformat(), end.isoformat()], text=True))
    finally:
        os.unlink(path)


def label_range(a, b):
    f = lambda d: d.strftime("%A, %B ") + str(d.day)
    return f"{f(a)} – {f(b)}"


def subject_for(city, shows):
    g = group(shows)
    runs = {}
    for s in shows:
        runs[(s["title"], s["v"])] = runs.get((s["title"], s["v"]), 0) + 1
    picks = [s for s in g if is_big(s, runs) and s.get("mi", 0) <= 20]
    ranked = sorted(picks, key=lambda p: min([i for i, w in enumerate(STARS) if w in p["title"].lower()] or [999]))
    names = []
    for p in ranked:
        n = p["who"] if p.get("who") and len(p["who"]) < len(p["title"]) else p["title"].split(":")[0].strip()
        if n not in names:
            names.append(n)
    short = city["short"]
    if len(names) >= 2:
        return f"{names[0]}, {names[1]} & more: {short} comedy this week"
    if names:
        return f"{names[0]} & more: {short} comedy this week"
    return f"This week's comedy in {city['name']}"


def ensure_city_list(name, folder_id, existing):
    full = CITY_LIST_PREFIX + name
    for l in existing:
        if l["name"] == full:
            return l["id"]
    return api("POST", "/contacts/lists", {"name": full, "folderId": folder_id})["id"]


def sync_list(list_id, emails):
    current = {c["email"].lower() for c in all_pages(f"/contacts/lists/{list_id}/contacts", "contacts")}
    want = {e.lower() for e in emails}
    add, drop = sorted(want - current), sorted(current - want)
    for i in range(0, len(add), 150):
        api("POST", f"/contacts/lists/{list_id}/contacts/add", {"emails": add[i:i + 150]})
    for i in range(0, len(drop), 150):
        api("POST", f"/contacts/lists/{list_id}/contacts/remove", {"emails": drop[i:i + 150]})


def main():
    today = datetime.date.today()
    start, end = week_window(today)
    week_key = start.isoformat()
    dry = os.environ.get("DRY_RUN") == "1"
    test_email, test_city = os.environ.get("TEST_EMAIL", "").strip(), os.environ.get("TEST_CITY", "").strip()
    limit = int(os.environ.get("DAILY_LIMIT", "290"))
    first = max(today, start)  # a Friday/Saturday catch-up run doesn't list days already past
    shows = shows_by_city(first, end)
    week = label_range(first, end)

    if test_email:
        city = BY_NAME.get(test_city.lower()) or BY_NAME["philadelphia"]
        cs = shows.get(city["code"], [])
        html = build(cs, city["name"], city["slug"], week)
        subj = "[TEST] " + subject_for(city, cs)
        print(f"Test: {city['name']} · {len(cs)} shows · {subj}")
        if dry:
            return
        lists = all_pages("/contacts/lists", "lists")
        main_list = next(l for l in lists if l["name"] == MAIN_LIST)
        camp = api("POST", "/emailCampaigns", {"name": f"TEST {city['name']} {week_key}", "subject": subj,
                                               "sender": SENDER, "htmlContent": html,
                                               "previewText": f"{len(cs)} shows within 50 miles, {week}",
                                               "recipients": {"listIds": [main_list["id"]]}})
        # Brevo only sends tests to existing contacts that are on some list: keep testers on a "Testers" list.
        testers = next((l for l in lists if l["name"] == "Testers"), None)
        tid = testers["id"] if testers else api("POST", "/contacts/lists", {"name": "Testers", "folderId": main_list.get("folderId") or 1})["id"]
        api("POST", "/contacts", {"email": test_email, "listIds": [tid], "updateEnabled": True})
        try:
            api("POST", f"/emailCampaigns/{camp['id']}/sendTest", {"emailTo": [test_email]})
        finally:
            api("DELETE", f"/emailCampaigns/{camp['id']}")  # tidy up the draft
        print("Test sent to", test_email)
        return

    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    if state.get("week") != week_key:
        state = {"week": week_key, "sent": {}}
    lists = all_pages("/contacts/lists", "lists")
    main_list = next((l for l in lists if l["name"] == MAIN_LIST), None)
    if not main_list:
        raise SystemExit(f"Brevo list '{MAIN_LIST}' not found")
    subs = [c for c in all_pages(f"/contacts/lists/{main_list['id']}/contacts", "contacts")
            if not c.get("emailBlacklisted")]
    by_city = {}
    for c in subs:
        city = BY_NAME.get(str((c.get("attributes") or {}).get("CITY", "")).strip().lower())
        if city:
            by_city.setdefault(city["code"], []).append(c["email"])
    todo = sorted([k for k in by_city if k not in state["sent"]], key=lambda k: -len(by_city[k]))
    print(f"Week of {week}: {len(subs)} subscribers in {len(by_city)} cities; to send now: {todo}")
    used = 0
    for code in todo:
        city = next(c for c in CITIES if c["code"] == code)
        emails, cs = by_city[code], shows.get(code, [])
        if not cs:
            print(f"- {city['name']}: no shows this week, skipped"); state["sent"][code] = "no-shows"; continue
        if used + len(emails) > limit:
            if used == 0 and len(emails) > limit:
                print(f"- {city['name']}: {len(emails)} subscribers is over the daily limit ({limit}); upgrade Brevo to send it")
            else:
                print(f"- {city['name']}: waits for the next run (daily limit)")
            continue
        subj = subject_for(city, cs)
        print(f"- {city['name']}: {len(emails)} subscribers, {len(cs)} shows · {subj}")
        if dry:
            continue
        lid = ensure_city_list(city["name"], main_list.get("folderId") or 1, lists)
        sync_list(lid, emails)
        camp = api("POST", "/emailCampaigns", {"name": f"{city['name']} weekly {week_key}", "subject": subj,
                                               "sender": SENDER, "htmlContent": build(cs, city["name"], city["slug"], week),
                                               "previewText": f"{len(cs)} shows within 50 miles, {week}",
                                               "recipients": {"listIds": [lid]}})
        api("POST", f"/emailCampaigns/{camp['id']}/sendNow")
        used += len(emails)
        state["sent"][code] = today.isoformat()
    if not dry:
        json.dump(state, open(STATE, "w"), indent=1)
    print(f"Sent {used} emails today.")


if __name__ == "__main__":
    main()
