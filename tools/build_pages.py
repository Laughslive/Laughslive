#!/usr/bin/env python3
"""Build LaughsLive's city pages, sitemap and robots.txt from index.html.

Run from the repository root after index.html has been updated:
    python3 tools/build_pages.py

It is safe to run repeatedly: blocks it inserts are wrapped in
<!--ll:NAME--> ... <!--/ll:NAME--> markers and replaced on each run.
Optional snippets (analytics, Google Search Console tag) go in
tools/head_extra.html; its contents are added to every page's <head>.
"""
import datetime, html, json, os, re, subprocess, sys, tempfile

SITE = "https://laughslive.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CITIES = [  # code, slug, display name, short name for titles, nearby places for the description
 ("NYC","new-york-city","New York City","NYC","Manhattan, Brooklyn, Queens, Long Island, Westchester and North Jersey"),
 ("PHL","philadelphia","Philadelphia","Philadelphia","the Main Line, Bucks County, South Jersey and Wilmington"),
 ("BOS","boston","Boston","Boston","Cambridge, Somerville, the North Shore, Worcester and Providence"),
 ("BAL","baltimore","Baltimore","Baltimore","Fells Point, Canton, Annapolis, Columbia and Towson"),
 ("DC","washington-dc","Washington, D.C.","Washington, D.C.","Arlington, Alexandria, Bethesda, National Harbor and Northern Virginia"),
 ("PIT","pittsburgh","Pittsburgh","Pittsburgh","the South Side, Homestead, the North Hills and Greensburg"),
 ("CLE","cleveland","Cleveland","Cleveland","Akron, Northfield Park, Kent and the East and West Sides"),
 ("NSH","nashville","Nashville","Nashville","Franklin, Murfreesboro, East Nashville and the Gulch"),
 ("PWM","portland-maine","Portland, Maine","Portland, Maine","South Portland, Westbrook, Biddeford and Brunswick"),
 ("CHI","chicago","Chicago","Chicago","Old Town, Wrigleyville, Schaumburg, Rosemont and the suburbs"),
 ("ATL","atlanta","Atlanta","Atlanta","Midtown, Buckhead, Sandy Springs, Alpharetta and Decatur"),
 ("RIC","richmond","Richmond","Richmond","Short Pump, the Fan, Scott's Addition and Henrico"),
 ("ORF","norfolk-virginia-beach","Norfolk & Virginia Beach","Norfolk & Virginia Beach","Hampton Roads, Chesapeake, Newport News and Hampton"),
 ("HFD","hartford","Hartford","Hartford","Manchester, West Hartford, New Britain and the Connecticut casinos"),
 ("NHV","new-haven","New Haven","New Haven","Bridgeport, Milford, the Connecticut shoreline and Waterbury"),
 ("MIA","miami","Miami","Miami","Miami Beach, Doral, Coral Gables, Fort Lauderdale and Hollywood"),
 ("TPA","tampa","Tampa","Tampa","Ybor City, St. Petersburg, Clearwater and Lakeland"),
 ("ORL","orlando","Orlando","Orlando","International Drive, Winter Park, Kissimmee and Sanford"),
 ("CIN","cincinnati","Cincinnati","Cincinnati","Northern Kentucky, Liberty Township, West Chester and Dayton"),
 ("STL","st-louis","St. Louis","St. Louis","Westport, Chesterfield, the Delmar Loop and St. Charles"),
 ("MSP","minneapolis-st-paul","Minneapolis–St. Paul","Minneapolis–St. Paul","Uptown, Bloomington, Northeast and the Twin Cities suburbs"),
 ("MKE","milwaukee","Milwaukee","Milwaukee","the Third Ward, Wauwatosa, Racine and Kenosha"),
 ("DET","detroit","Detroit","Detroit","Royal Oak, Ferndale, Ann Arbor and Windsor"),
 ("DEN","denver","Denver","Denver","LoDo, RiNo, Boulder, Aurora, Lakewood and the Denver Tech Center"),
 ("IND","indianapolis","Indianapolis","Indianapolis","Broad Ripple, Fountain Square, Carmel, Fishers and Bloomington"),
 ("AUS","austin","Austin","Austin","Sixth Street, East Austin, South Congress, Round Rock and San Marcos"),
 ("DFW","dallas-fort-worth","Dallas–Fort Worth","Dallas–Fort Worth","Deep Ellum, Addison, Plano, Arlington, Fort Worth and Frisco"),
 ("PHX","phoenix","Phoenix","Phoenix","Scottsdale, Tempe, Mesa, Chandler and Glendale"),
 ("LAS","las-vegas","Las Vegas","Las Vegas","the Strip, Downtown and Fremont Street, Henderson and Summerlin"),
]
REGIONS = [("Northeast",["BOS","HFD","NHV","NYC","PHL","PWM"]),("Mid-Atlantic",["BAL","ORF","PIT","RIC","DC"]),
           ("South",["ATL","AUS","DFW","MIA","NSH","ORL","TPA"]),("Midwest",["CHI","CIN","CLE","DET","IND","MKE","MSP","STL"]),
           ("West",["DEN","LAS","PHX"])]
BY = {c[0]: c for c in CITIES}

def block(name, content):
    return f"<!--ll:{name}-->{content}<!--/ll:{name}-->"

def put_block(page, name, content, before):
    """Replace an existing marked block, or insert it before the `before` string."""
    pat = re.compile(r"<!--ll:%s-->.*?<!--/ll:%s-->" % (name, name), re.S)
    new = block(name, content)
    if pat.search(page):
        return pat.sub(lambda m: new, page, count=1)
    i = page.index(before)
    return page[:i] + new + "\n" + page[i:]

def strip_blocks(page):
    return re.sub(r"<!--ll:(\w+)-->.*?<!--/ll:\1-->\n?", "", page, flags=re.S)

def city_shows():
    """Run the page's own data code in node and return upcoming shows per city."""
    src = strip_blocks(open(os.path.join(ROOT, "index.html"), encoding="utf-8").read())
    start = src.rindex("<script>") + len("<script>")
    js = src[start: src.rindex("</script>")]
    js = js[: js.index("function render")]
    js += r"""
const out={};
for(const c in CENTER){
  out[c]=SHOWS.filter(s=>miles(CENTER[c],[s.v.lat,s.v.lng])<=RADIUS&&s.d>=todayStr)
    .sort((a,b)=>(a.d+a.t).localeCompare(b.d+b.t)).slice(0,40)
    .map(s=>({d:s.d,t:s.t,title:s.title,who:s.who,venue:s.v.n,area:s.v.area,b:s.v.b}));
}
console.log(JSON.stringify(out));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js)
        path = f.name
    try:
        return json.loads(subprocess.check_output(["node", path], text=True))
    finally:
        os.unlink(path)

def fmt_when(d, t):
    dt = datetime.datetime.strptime(d + " " + t, "%Y-%m-%d %H:%M")
    return dt.strftime("%a, %b ") + str(dt.day) + " · " + dt.strftime("%I:%M %p").lstrip("0")

def static_list(code, shows):
    name = BY[code][2]
    items = "".join(
        f"<li><b>{html.escape(s['title'])}</b> — {fmt_when(s['d'], s['t'])} — "
        f"{html.escape(s['venue'])}, {html.escape(s['area'])}</li>" for s in shows)
    return (f'<section class="seo-list"><h2>Upcoming comedy shows in {html.escape(name)}</h2>'
            f"<ul>{items}</ul></section>")

def nav_html(current=None):
    groups = []
    for region, codes in REGIONS:
        links = " · ".join(
            (f"<b>{html.escape(BY[c][2])}</b>" if c == current else
             f'<a href="/{BY[c][1]}/">{html.escape(BY[c][2])}</a>') for c in codes)
        groups.append(f"<p><span>{region}:</span> {links}</p>")
    home = "" if current is None else ' · <a href="/">All cities</a>'
    return ('<nav class="citylinks" aria-label="Comedy shows by city"><style>'
            ".citylinks{margin-top:36px;font-size:14px;color:var(--muted)}"
            ".citylinks h2{font-size:15px;margin:0 0 6px;color:var(--ink)}"
            ".citylinks p{margin:4px 0}.citylinks span{font-weight:600}"
            ".citylinks a{color:var(--accent)}.citylinks b{color:var(--ink)}"
            f"</style><h2>Comedy shows by city{home}</h2>{''.join(groups)}</nav>")

def head_html(title, desc, url):
    extra = ""
    p = os.path.join(ROOT, "tools", "head_extra.html")
    if os.path.exists(p):
        extra = open(p, encoding="utf-8").read().strip()
    e = html.escape
    return (f'<link rel="canonical" href="{url}">'
            f'<meta property="og:type" content="website"><meta property="og:site_name" content="LaughsLive">'
            f'<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">'
            f'<meta property="og:url" content="{url}"><meta name="twitter:card" content="summary">'
            '<link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#0A0E22">'
            '<link rel="icon" type="image/png" sizes="32x32" href="/icons/favicon-32.png">'
            '<link rel="icon" type="image/png" sizes="192x192" href="/icons/icon-192.png">'
            '<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">'
            '<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">'
            '<meta name="apple-mobile-web-app-title" content="LaughsLive">'
            '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
            '<script>window.LL_SITE=1;if("serviceWorker"in navigator)addEventListener("load",()=>navigator.serviceWorker.register("/sw.js").catch(()=>{}))</script>'
            '<script defer src="/install.js"></script>'
            f"{extra}")

def set_title_desc(page, title, desc):
    page = re.sub(r"<title>.*?</title>", lambda m: f"<title>{html.escape(title)}</title>", page, count=1, flags=re.S)
    page = re.sub(r'<meta name="description" content="[^"]*">',
                  lambda m: f'<meta name="description" content="{html.escape(desc)}">', page, count=1)
    return page

def main():
    today = datetime.date.today().isoformat()
    index_path = os.path.join(ROOT, "index.html")
    base = strip_blocks(open(index_path, encoding="utf-8").read())
    shows = city_shows()

    # Home page
    title = "LaughsLive: Comedy Shows Near You"
    desc = ("Find upcoming stand-up comedy, improv and live podcast shows near you, in cities including New York, "
            "Chicago, Las Vegas, Austin, Dallas, Boston, Philadelphia, Washington D.C., Atlanta, Denver and Miami.")
    home = set_title_desc(base, title, desc)
    home = put_block(home, "head", head_html(title, desc, SITE + "/"), "</head>")
    home = put_block(home, "nav", nav_html(), "<footer>")
    open(index_path, "w", encoding="utf-8").write(home)

    # City pages
    for code, slug, name, short, nearby in CITIES:
        url = f"{SITE}/{slug}/"
        n = len(shows.get(code, []))
        title = f"Comedy Shows in {short}: Stand-Up Tonight & This Week | LaughsLive"
        desc = (f"Upcoming comedy shows in {name} and within 50 miles, including {nearby}. "
                "Club showcases, touring headliners and live podcasts, with links to the venue's own tickets.")
        pg = set_title_desc(base, title, desc)
        pg = put_block(pg, "head", head_html(title, desc, url) + f"<script>window.LL_CITY={json.dumps(code)}</script>", "</head>")
        pg = pg.replace('<option value="NYC" selected>', '<option value="NYC">', 1)
        pg = pg.replace(f'<option value="{code}">', f'<option value="{code}" selected>', 1)
        pg = re.sub(r'(<input id="loc"[^>]*?) value="[^"]*"', r'\1 value=""', pg, count=1)
        pg = re.sub(r'<p class="tag">.*?</p>',
                    lambda m: f'<p class="tag">Comedy shows in {html.escape(name)} and up to 50 miles around it, '
                              f'from club showcases to arena headliners. Enter where you are to see what\'s closest.</p>',
                    pg, count=1, flags=re.S)
        pg = pg.replace('<main id="results"></main>',
                        f'<main id="results">{static_list(code, shows.get(code, []))}</main>', 1)
        pg = put_block(pg, "nav", nav_html(code), "<footer>")
        os.makedirs(os.path.join(ROOT, slug), exist_ok=True)
        open(os.path.join(ROOT, slug, "index.html"), "w", encoding="utf-8").write(pg)
        print(f"{slug}: {n} shows in static list")

    urls = [SITE + "/"] + [f"{SITE}/{c[1]}/" for c in CITIES]
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq></url>\n" for u in urls)
          + "</urlset>\n")
    open(os.path.join(ROOT, "sitemap.xml"), "w").write(sm)
    open(os.path.join(ROOT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    print("wrote sitemap.xml and robots.txt")

if __name__ == "__main__":
    main()
