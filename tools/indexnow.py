#!/usr/bin/env python3
"""Tell IndexNow search engines (Bing, Yandex, Seznam, Naver…) that every page in sitemap.xml changed."""
import json, re, sys, urllib.request
KEY = "ffb2c0a04a20e46c005ce948422542e3"   # also served at https://laughslive.com/ffb2c0a04a20e46c005ce948422542e3.txt
urls = re.findall(r"<loc>(.*?)</loc>", open("sitemap.xml").read())
body = json.dumps({"host": "laughslive.com", "key": KEY,
                   "keyLocation": f"https://laughslive.com/{KEY}.txt", "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                             headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("IndexNow response:", r.status, "for", len(urls), "pages")
except Exception as e:   # never fail the site update because of this
    print("IndexNow notice failed:", e); sys.exit(0)
