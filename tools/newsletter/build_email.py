"""Build a LaughsLive weekly newsletter email (HTML) for one city.

Input: a JSON list of shows for that city and week, as exported from the site's own data:
  {d, t, title, who, v, area, b, head, type, flags, url, label, mi, price}
Usage: python3 build_email.py shows.json "Philadelphia" philadelphia "November 15–22" out.html

Email-safe: table layout, inline styles, light background. Brevo replaces {{ unsubscribe }}.
"""
import html, json, sys, datetime
from collections import OrderedDict

PINK = "#E0207F"; INK = "#14182E"; MUTED = "#5B6380"; LINE = "#E6E8F0"; BG = "#F4F5FA"
SHOWCASE = ("allstars", "all stars", "showcase", "presents", "open mic", "storyslam", "the moth", "crime scene", "rock bottom", "beer run")


def fmt_time(t):
    h, m = map(int, t.split(":"))
    ap = "AM" if h < 12 else "PM"
    h = h % 12 or 12
    return f"{h}:{m:02d}" if m else f"{h}", ap


def times_text(ts):
    parts = [fmt_time(t) for t in sorted(set(ts))]
    aps = {ap for _, ap in parts}
    if len(aps) == 1:
        return " & ".join(p for p, _ in parts) + " " + parts[0][1]
    return " & ".join(f"{p} {ap}" for p, ap in parts)


def group(shows):
    """Merge same show + venue + day into one line with several times."""
    out = OrderedDict()
    for s in sorted(shows, key=lambda s: (s["d"], s["t"])):
        k = (s["d"], s["title"], s["v"])
        if k not in out:
            out[k] = dict(s, times=[], soldout=[])
        out[k]["times"].append(s["t"])
        if "out" in (s.get("flags") or []):
            out[k]["soldout"].append(s["t"])
    return list(out.values())


CLUB = ("comedy", "punch line", "punchline", "helium", "improv", "funny bone", "zanies", "laugh", "cellar", "hyena")


def is_big(s, runs):
    """A headliner at a theater/arena, or a club headliner playing 3+ shows this week."""
    t = s["title"].lower()
    if not s.get("head") or any(w in t for w in SHOWCASE):
        return False
    club = any(w in s["v"].lower() for w in CLUB)
    return (not club) or runs.get((s["title"], s["v"]), 0) >= 3


def esc(x):
    return html.escape(x or "")


def dlabel(d):
    day = datetime.date.fromisoformat(d)
    return day.strftime("%a %b ") + str(day.day)


def line(s, show_day=False, run=None):
    if run and len(set(run)) > 1:
        ds = sorted(set(run))
        when = f"{dlabel(ds[0])} – {dlabel(ds[-1])} · {len(run)} shows"
    else:
        when = (dlabel(s["d"]) + " · " if show_day else "") + times_text(s["times"])
    who = f'<div style="color:{MUTED};font-size:14px">{esc(s["who"])}</div>' if s.get("who") and s["who"] != s["title"] else ""
    sold = ' <span style="color:#B42318;font-weight:700">· sold out</span>' if s["soldout"] and len(s["soldout"]) == len(s["times"]) else ""
    far = f' · {s["mi"]:.0f} mi' if s.get("mi", 0) >= 15 else ""
    return f'''<tr><td style="padding:12px 0;border-top:1px solid {LINE}">
<div style="font-size:13px;font-weight:700;color:{PINK};letter-spacing:.3px">{esc(when)}{sold}</div>
<div style="font-size:17px;font-weight:700;color:{INK};margin:2px 0">{esc(s["title"])}</div>{who}
<div style="color:{MUTED};font-size:14px">{esc(s["v"])} · {esc(s["area"])}{far}</div>
<div style="margin-top:6px"><a href="{esc(s["url"])}" style="color:{PINK};font-weight:700;font-size:14px;text-decoration:none">{esc(s["label"] or "Tickets & info")} →</a></div>
</td></tr>'''


def build(shows, city, slug, week):
    g = group(shows)
    runs = {}
    for s in shows:
        runs[(s["title"], s["v"])] = runs.get((s["title"], s["v"]), 0) + 1
    big = sorted([s for s in g if is_big(s, runs)], key=lambda s: (s.get("mi", 0) > 20, s["d"], s["t"]))
    # Big shows: one entry per act (first date), up to 6, closest/biggest first by date.
    seen, picks = set(), []
    for s in big:
        key = s["title"].split(":")[0].strip().lower()
        if key in seen:
            continue
        seen.add(key); picks.append(s)
    picks = picks[:6]
    days = OrderedDict()
    for s in g:
        days.setdefault(s["d"], []).append(s)
    day_html = ""
    for d, arr in days.items():
        dt = datetime.date.fromisoformat(d)
        day_html += f'<tr><td style="padding:22px 0 4px;font-size:15px;font-weight:800;color:{INK};text-transform:uppercase;letter-spacing:1px">{dt.strftime("%A")} <span style="color:{MUTED};font-weight:600;text-transform:none;letter-spacing:0">{dt.strftime("%B")} {dt.day}</span></td></tr>'
        day_html += "".join(line(s) for s in arr)
    picks_html = "".join(line(s, show_day=True, run=[x["d"] for x in shows if x["title"] == s["title"] and x["v"] == s["v"]]) for s in picks)
    n = len(shows)
    url = f"https://laughslive.com/{slug}/"
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Comedy in {esc(city)} this week</title></head>
<body style="margin:0;padding:0;background:{BG};font-family:Helvetica,Arial,sans-serif">
<div style="display:none;max-height:0;overflow:hidden">{n} comedy shows in the {esc(city)} area, {esc(week)}.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BG}"><tr><td align="center" style="padding:20px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:14px;overflow:hidden">
<tr><td style="background:#0A0E22;padding:22px 24px">
<a href="https://laughslive.com/" style="text-decoration:none"><img src="https://laughslive.com/icons/icon-192.png" width="40" height="40" alt="" style="vertical-align:middle;border-radius:9px;border:0">
<span style="vertical-align:middle;color:#ffffff;font-size:22px;font-weight:800;letter-spacing:1px;margin-left:10px">LAUGHS<span style="color:#FF3EA5">LIVE</span></span></a>
</td></tr>
<tr><td style="padding:26px 24px 6px">
<div style="font-size:26px;font-weight:800;color:{INK};line-height:1.2">Comedy in {esc(city)} this week</div>
<div style="font-size:15px;color:{MUTED};margin-top:6px">{esc(week)} · {n} shows within 50 miles</div>
</td></tr>
<tr><td style="padding:10px 24px 0"><div style="font-size:13px;font-weight:800;color:{PINK};text-transform:uppercase;letter-spacing:1.5px">Big shows</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{picks_html}</table></td></tr>
<tr><td style="padding:18px 24px 0"><div style="font-size:13px;font-weight:800;color:{PINK};text-transform:uppercase;letter-spacing:1.5px">Every show this week</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{day_html}</table></td></tr>
<tr><td align="center" style="padding:26px 24px">
<a href="{url}" style="display:inline-block;background:{PINK};color:#ffffff;font-weight:700;font-size:16px;padding:13px 24px;border-radius:999px;text-decoration:none">See all {esc(city)} shows</a>
<div style="color:{MUTED};font-size:13px;margin-top:12px">Times and lineups change, so check the venue's page before you go.</div>
</td></tr>
<tr><td style="background:{BG};padding:18px 24px;color:{MUTED};font-size:12px;line-height:1.6;text-align:center">
You're getting this because you signed up at laughslive.com for {esc(city)} shows.<br>
<a href="{{{{ unsubscribe }}}}" style="color:{MUTED}">Unsubscribe</a> · <a href="https://laughslive.com/privacy/" style="color:{MUTED}">Privacy</a> · <a href="mailto:info@laughslive.com" style="color:{MUTED}">info@laughslive.com</a><br>
LaughsLive · 3103 Hulmeville Road, Suite 200 · Bensalem, PA 19020
</td></tr>
</table></td></tr></table></body></html>'''


if __name__ == "__main__":
    src, city, slug, week, out = sys.argv[1:6]
    shows = json.load(open(src))
    open(out, "w").write(build(shows, city, slug, week))
    print("wrote", out)
