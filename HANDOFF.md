# LaughsLive — handoff notes

Background for a new Claude chat picking up this project, or starting a sister site
(e.g. a reggae version) from this code. Read this, then `tools/ADDING_A_CITY.md` and
`tools/update/east.md`.

## What the site is
- **laughslive.com**: a "Bandsintown for comedy". Find stand-up, improv and live-podcast shows
  within 50 miles of 34 US cities. Venue-first and privacy-first.
- Repo **Laughslive/Laughslive** (branch `main`), served by **GitHub Pages**. Domain is at GoDaddy.
- **`index.html` is the source of truth** for all show data. An old claude.ai artifact copy exists
  but is no longer updated.

## Owner's standing rules
- **Privacy first.**
  - No cookies, no accounts, no GPS, no ad trackers.
  - The owner won't give a phone number to Google, TikTok or Instagram.
  - Never put the owner's personal email anywhere public or send it to outside services.
- **Venue first.**
  - The venue's own calendar, or its official ticket seller, is the main source and the link fans get.
  - Listing and resale sites (comedy.tickets, theater.guide, seatgeek, etc.) are backup only.
- **Ticket buttons:**
  - "Tickets & info" goes to the show's own page.
  - "Tickets at venue" goes to the venue's site (`SITES`).
  - "Find tickets" (a Google search) is the last resort.
- **Accuracy:** never guess times, prices, names or URLs. Skip a show if no source gives its start time.
- **Excluded:** magic and hypnotist acts, Popovich Comedy Pet Theater, Tape Face, open mics,
  drag brunches, music acts.
- **Declined:** The Comedy Bar Fort Lauderdale. Shane Gillis and Matt & Shane's Secret Podcast are
  not on the tour-tracking list (their dates on venue calendars are fine).
- **Secrets** (API keys) go in GitHub Actions secrets, never in code; the repo is public.
- **Before acting:** explain GitHub steps in plain words, and ask before anything irreversible.
- **Commits:**
  - Author: `-c user.name="LaughsLive" -c user.email="laughslive@users.noreply.github.com"`.
  - Messages end with a `Co-Authored-By:` line.

## How the data works (last `<script>` in index.html)
- **`V`**: venues `{n, area, b, c, lat, lng}`.
  - Coordinates decide which city a venue appears under (within 50 miles).
  - The block between `// <tm-venues>` and `// </tm-venues>` is generated. Add hand-checked venues above it.
  - Hand rows must use hand venues, not `tm_*` keys, because those keys are rebuilt each update.
- **`SITES`**: venue key → official calendar URL. `LISTING_SITE` is the regex of aggregator domains.
- **`RAW`**: rows `[date, "HH:MM|HH:MM", title, performers, venueKey, S/I/P, url, price|null, flags]`.
  - Grouped under `// City` comment headers.
  - The block between `// <tm>` and `// </tm>` is generated. Hand rows always win.
- **City setup** lives in several places: `CENTER`, `CITY_NAME`, `CITY_SLUG`, the `*_PLACES` tables,
  `ZIP_PREFIX`, the dropdown groups, and `data/cities.json`, which is the single city list checked
  by the build. Follow `tools/ADDING_A_CITY.md`.
- **Features:**
  - Comedian search: `?comic=`, word-prefix match.
  - Headliners-only filter.
  - City pages at `/<slug>/`.
  - About and Privacy pages, built from `tools/pages/`.
  - Install as an app: PWA with `manifest.webmanifest`, `sw.js` and `install.js`.

## Tools and automation
- `tools/check_script.py`: syntax-checks the app script (runs `node --check`).
- `tools/build_pages.py`:
  - Builds the city pages, About/Privacy, `sitemap.xml` and `robots.txt`.
  - Pulls in `tools/head_extra.html` (Google verification and the Cloudflare analytics beacon).
- `tools/fetch_ticketmaster.py` and `tools/merge_ticketmaster.py`:
  - Ticketmaster Discovery API, comedy genre, about 70 days ahead.
  - Matches venues by name within 5 miles, with a state check.
- **GitHub Actions:**
  - `ticketmaster.yml`: daily at 09:17 UTC, plus a manual run. Fetches, merges, checks, builds, pushes, then pings IndexNow.
  - `indexnow.yml`: runs on each push.
  - Secret: `TM_API_KEY`.
- **Twice-weekly Claude scheduled tasks** (Sundays and Wednesdays):
  - **East:** 7:33 AM ET. Northeast, Mid-Atlantic and South, plus the comedian tour check.
  - **West:** 2:41 PM ET. Midwest and West.
  - They follow `tools/update/east.md` and `tools/update/west.md`.
  - The web reader can only open URLs that appear in a search result or in the task's own prompt.
    So the task prompts list every approved venue and comedian URL. When adding venues or
    comedians, update both the .md file and the task prompt.
- **This sandbox's shell can't reach websites** (git and gh work). Use WebSearch/WebFetch.
  Many calendars load by script; see the fetching tips in `east.md`.

## Accounts and setup (all done)
- **Google Search Console:** verified by meta tag. **Bing Webmaster:** set up. **IndexNow:** key file at the site root.
- **Cloudflare Web Analytics:** cookieless; the beacon is in `head_extra.html`.
- **Email:** Proton custom domain. info@laughslive.com (general and advertising) and
  shows@laughslive.com (show submissions). The Proton plan allows one custom domain, which this site uses.
- **Newsletter:** Brevo chosen, not yet connected. Connecting it needs DNS records at GoDaddy
  (merge with the existing SPF record) and the API key stored as a GitHub secret. Newsletters need a
  postal address (CAN-SPAM); the owner plans a PO box.
- **Social:** pending. The owner won't give out a phone number (prepaid number suggested).
- **Hosting is free** (GitHub Pages). The site keeps running without a Claude subscription, but the
  twice-weekly Claude updates would stop. The Ticketmaster Action keeps running.

## Starting a sister site (e.g. reggae)
1. **Copy the code.** Create a new repo, copy this one, and rename LaughsLive throughout: name, logo,
   colors, manifest, icons, `head_extra.html` (new Search Console tag and Cloudflare beacon), CNAME
   and the About/Privacy pages.
2. **Reset the data.** Clear `RAW` and the hand venues in `V`. Pick cities in `data/cities.json`.
3. **Ticketmaster.** Change the genre in `tools/fetch_ticketmaster.py` from comedy to the right
   music genre (look up the Discovery API classification). Rework the EXCLUDE filter in the merge
   script. Add the `TM_API_KEY` secret to the new repo.
4. **Sourcing.** Expect fewer dedicated venues than comedy. Many shows are at general music venues,
   festivals, lounges and promoter nights on Eventbrite, Dice and Instagram. Artist tour pages and
   promoters matter more than venue calendars.
5. **Last.** New domain, DNS, Search Console, Bing, IndexNow key, and scheduled update tasks with
   their own URL lists.
