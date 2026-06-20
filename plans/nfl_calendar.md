# NFL 2026-2027 iCal Calendar

Build a subscribable `.ics` calendar for the complete 2026-2027 NFL season (preseason + regular season + playoffs), hosted on GitHub Pages and refreshed every 15 minutes via GitHub Actions, with live and final scores and a 🏈 last-updated banner.

**Subscribe URL:** `https://robtomlinson.github.io/nfl-calendar/nfl_2026.ics`

## For Future Agents

As work proceeds: mark checkboxes `- [x]` as items complete; when a phase is done, set its status to `Complete` and write its **Phase Summary** (what was done, key decisions, anything needed to continue with zero context); run the phase's **Verification Plan** and record the result before moving on. When all phases are done, fill in **Final Recap** and **Deployment Plan**.

---

## Key Design Decisions

- **Timezone:** All game times stored as UTC (`Z` suffix). iPhone Calendar auto-converts to the viewer's current local timezone — works correctly while traveling with no configuration.
- **Data source:** ESPN unofficial public API, no key required.
  - Week schedule: `https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype={type}&week={n}&dates=2026`
  - Live scoreboard: `https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard`
  - Season types: `1` = preseason (weeks 1–4), `2` = regular season (weeks 1–18), `3` = playoffs (weeks 1–5)
- **Hosting:** GitHub Pages (branch: `gh-pages`), deployed by `peaceiris/actions-gh-pages@v4`.
- **Update cadence:** GitHub Actions cron every 15 minutes. Public repo = unlimited minutes.
- **Cache strategy:** GitHub Actions cache stores `cache/schedule.json` keyed by ISO year-week (`2026-38`). Full 27-week season fetch only on weekly cache miss (~30 sec, 1 req/sec). Every run fetches live scoreboard (1 req).
- **Live score display:** SUMMARY line updates to `NE 14 @ SEA 21 (Live)` or `NE 14 @ SEA 28 (Final)`; SEQUENCE increments on each change so clients update in place.
- **Last-updated event:** Stable UID `nfl-2026-last-updated@espn.com`, all-day banner (`DTSTART;VALUE=DATE`), `TRANSP:TRANSPARENT`, SEQUENCE increments each run. Shows as 🏈 banner at top of the current day, moves forward each refresh.
- **International games:** Week 1 has SF @ LAR at Melbourne Cricket Ground. If `country` ≠ `US`/`USA`, use `city, country` instead of `city, state` in LOCATION/DESCRIPTION.

---

## Phase 1: Project Scaffold
Status: Not started

- [ ] Create directory structure: `src/`, `docs/`, `cache/`, `.github/workflows/`
- [ ] Write `requirements.txt` with `icalendar>=5.0` and `requests>=2.31`
- [ ] Write `.gitignore` (exclude `cache/`, `__pycache__/`, `*.pyc`, `.env`)
- [ ] Write `docs/index.html` — simple page with subscribe URL `https://robtomlinson.github.io/nfl-calendar/nfl_2026.ics` and iPhone instructions
- [ ] Write `README.md` with project overview and subscribe link

### Verification Plan
- `ls src/ docs/ .github/workflows/` → all directories exist
- `cat requirements.txt` → contains `icalendar` and `requests`
- `cat .gitignore` → contains `cache/` entry

### Phase Summary
_(write when phase completes)_

---

## Phase 2: ESPN API Fetch Layer (`src/fetch.py`)
Status: Not started

- [ ] Implement `fetch_week(season_type, week, season_year=2026) -> dict` — GET scoreboard with `seasontype`/`week`/`dates` params, 30s timeout, raise on HTTP error
- [ ] Implement `fetch_scoreboard() -> dict` — GET current week live scoreboard (no params)
- [ ] Implement `fetch_full_season(year=2026) -> list[dict]` — iterate type 1 weeks 1–4, type 2 weeks 1–18, type 3 weeks 1–5; `time.sleep(1)` between each; skip weeks that return 0 events (future playoff rounds)
- [ ] Implement `parse_game(event) -> dict` — extract from ESPN event object:
  - `id`, `date` (UTC ISO 8601)
  - `away_abbr`, `away_name`, `home_abbr`, `home_name`
  - `venue`, `city`, `state`, `country`
  - `networks` (list of strings from `broadcasts[].names[]`)
  - `status` (`STATUS_SCHEDULED` | `STATUS_IN_PROGRESS` | `STATUS_FINAL`)
  - `status_detail` (human-readable detail string, e.g. `"Thu, Sep 10th at 8:20 PM EDT"`)
  - `away_score`, `home_score`
  - `_sequence` (initialize to 0; caller bumps when data changes)

### Verification Plan
- `python -c "from src.fetch import fetch_scoreboard, parse_game; d=fetch_scoreboard(); g=parse_game(d['events'][0]); print(g)"` → prints a game dict with all keys present
- `python -c "from src.fetch import fetch_week, parse_game; d=fetch_week(2,1); print(len(d['events']), 'games')"` → prints `10 games` (Week 1 regular season)
- `python -c "from src.fetch import fetch_week; d=fetch_week(1,1); print(d['events'][0]['name'])"` → prints a preseason game name

### Phase Summary
_(write when phase completes)_

---

## Phase 3: iCal Generation (`src/calendar_gen.py`)
Status: Not started

- [ ] Implement `game_to_event(game: dict) -> Event` using the `icalendar` library:
  - `UID`: `nfl-2026-{game['id']}@espn.com`
  - `SEQUENCE`: `game['_sequence']`
  - `DTSTAMP`: current UTC (required by RFC 5545)
  - `DTSTART`/`DTEND`: parse `game['date']` as UTC; DTEND = DTSTART + 3.5 hours
  - `SUMMARY`:
    - Scheduled: `NE @ SEA`
    - In-progress: `NE 14 @ SEA 21 (Live)`
    - Final: `NE 14 @ SEA 28 (Final)`
  - `LOCATION`: `Lumen Field, Seattle, WA` (or `Melbourne Cricket Ground, Melbourne, Australia` for international)
  - `DESCRIPTION`: full team names, venue, TV networks, score/status detail
  - `TRANSP`: `OPAQUE` (games block time)
  - `LAST-MODIFIED`: current UTC
- [ ] Implement `last_updated_event(updated_at: datetime) -> Event`:
  - `UID`: `nfl-2026-last-updated@espn.com` (stable — clients update in-place)
  - `SEQUENCE`: seconds since 2026-01-01 UTC divided by 900 (increments each 15-min run)
  - `DTSTART;VALUE=DATE`: today's UTC date
  - `DTEND;VALUE=DATE`: tomorrow's UTC date
  - `SUMMARY`: `🏈 Updated {Mon Sep 10 3:15 PM UTC}`
  - `TRANSP`: `TRANSPARENT` (non-blocking, shows as light banner)
  - `DTSTAMP` + `LAST-MODIFIED`: current UTC
- [ ] Implement `build_calendar(games: list[dict], updated_at: datetime) -> bytes`:
  - Calendar props: `PRODID:-//NFL 2026 Calendar//EN`, `VERSION:2.0`, `CALSCALE:GREGORIAN`, `METHOD:PUBLISH`, `X-WR-CALNAME:NFL 2026-2027`, `REFRESH-INTERVAL;VALUE=DURATION:PT15M`, `X-PUBLISHED-TTL:PT15M`
  - Add one VEVENT per game (sorted by date)
  - Add `last_updated_event(updated_at)`
  - Return `.to_ical()` bytes

### Verification Plan
- `python -c "from src.fetch import fetch_week, parse_game; from src.calendar_gen import game_to_event; g=parse_game(fetch_week(2,1)['events'][0]); e=game_to_event(g); print(e.to_ical().decode())"` → prints a valid VEVENT block with UID, DTSTART (UTC Z), SUMMARY, LOCATION, DESCRIPTION
- `python -c "from src.fetch import fetch_week, parse_game; from src.calendar_gen import build_calendar; from datetime import datetime, timezone; gs=[parse_game(e) for e in fetch_week(2,1)['events']]; cal=build_calendar(gs, datetime.now(timezone.utc)); print(cal.decode()[:500])"` → prints valid iCal header and first VEVENT
- Manually verify: SUMMARY for a scheduled game reads `ABB @ ABB`; LOCATION contains venue + city/state

### Phase Summary
_(write when phase completes)_

---

## Phase 4: Orchestration (`src/main.py`)
Status: Not started

- [ ] Load `cache/schedule.json` if it exists (dict of `{game_id: game_dict}` + `fetched_at` timestamp)
- [ ] Determine if full refresh needed: `fetched_at` absent or older than 7 days
- [ ] If full refresh: call `fetch_full_season()`, parse all events, merge into `games_by_id`
- [ ] Always: call `fetch_scoreboard()`, parse events, merge into `games_by_id`:
  - Compare incoming game to cached game; if `status` or score changed → increment `_sequence`
- [ ] Save updated `cache/schedule.json`
- [ ] Sort `games_by_id.values()` by `date`, call `build_calendar(games, now)`, write to `docs/nfl_2026.ics`
- [ ] Print summary: total games, how many live, how many final

**`cache/schedule.json` structure:**
```json
{
  "fetched_at": "2026-09-10T15:00:00Z",
  "games": {
    "401547417": { ...game dict... }
  }
}
```

### Verification Plan
- `python src/main.py` → exits 0, prints game count (expect 250+ across full season), creates `docs/nfl_2026.ics`
- `wc -l docs/nfl_2026.ics` → large file (thousands of lines)
- `grep -c "BEGIN:VEVENT" docs/nfl_2026.ics` → ≥ 250 (all games + 1 last-updated event)
- `grep "🏈" docs/nfl_2026.ics` → finds the last-updated VEVENT SUMMARY line
- `grep "STATUS_FINAL\|STATUS_IN_PROGRESS" docs/nfl_2026.ics` → should be absent (status is used internally; only the display strings appear in SUMMARY)

### Phase Summary
_(write when phase completes)_

---

## Phase 5: GitHub Actions Workflow
Status: Not started

- [ ] Create `.github/workflows/update_calendar.yml` with:
  - Triggers: `schedule: cron: '*/15 * * * *'` + `workflow_dispatch`
  - `permissions: contents: write`
  - Steps:
    1. `actions/checkout@v4`
    2. `actions/setup-python@v5` (python 3.12, pip cache)
    3. `pip install -r requirements.txt`
    4. Compute ISO week: `echo "week=$(date -u +'%G-%V')" >> $GITHUB_OUTPUT`
    5. `actions/cache@v4` restore — path `cache/schedule.json`, key `nfl-schedule-{week}`, restore-keys `nfl-schedule-`
    6. `python src/main.py`
    7. `actions/cache/save@v4` — same path/key
    8. `peaceiris/actions-gh-pages@v4` — publish `./docs` to `gh-pages`, `force_orphan: false`

### Verification Plan
- `cat .github/workflows/update_calendar.yml` → valid YAML, contains `*/15 * * * *`, `peaceiris/actions-gh-pages`, cache steps
- After pushing to GitHub: Actions tab shows workflow run succeeded within 2 minutes of push
- `gh-pages` branch contains `nfl_2026.ics` and `index.html`
- `curl -I https://robtomlinson.github.io/nfl-calendar/nfl_2026.ics` → HTTP 200

### Phase Summary
_(write when phase completes)_

---

## Phase 6: Repository Setup & Subscription
Status: Not started

> **Note:** Python is not installed in the Claude Code session environment on this machine.
> Local verification must be done by the user running `pip install -r requirements.txt && python src/main.py` from the project root.

- [ ] User installs Python 3.10+ and runs `pip install -r requirements.txt` locally
- [ ] User runs `python src/main.py` from project root — expect 250+ games, `docs/nfl_2026.ics` generated
- [ ] Initialize git repo: `git init && git add . && git commit -m "Initial commit"`
- [ ] Create GitHub repo `robtomlinson/nfl-calendar` (public) via `gh repo create robtomlinson/nfl-calendar --public --source=. --push`
- [ ] Enable GitHub Pages: Settings → Pages → Source: Deploy from branch → `gh-pages` / `(root)`
- [ ] Trigger first workflow run manually (Actions → Update NFL Calendar → Run workflow)
- [ ] Confirm `https://robtomlinson.github.io/nfl-calendar/nfl_2026.ics` is accessible
- [ ] Subscribe on iPhone: Settings → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar → enter URL

### Verification Plan
- `grep -c "BEGIN:VEVENT" docs/nfl_2026.ics` → ≥ 250
- `grep "🏈" docs/nfl_2026.ics` → finds the last-updated event SUMMARY
- `curl -s https://robtomlinson.github.io/nfl-calendar/nfl_2026.ics | head -5` → first line is `BEGIN:VCALENDAR`
- Open iPhone Calendar, verify games appear with correct local times, venue, and TV network in event detail
- On a game day: verify SUMMARY updates to show live score within ~15 minutes of kickoff
- Verify 🏈 banner appears at top of today's date

### Phase Summary
_(write when phase completes)_

---

## Final Recap
_(write when all phases complete)_

## Deployment Plan
_(write when all phases complete)_
