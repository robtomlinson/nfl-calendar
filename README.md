# NFL 2026-2027 iCal Calendar

Subscribable calendar for the complete 2026-2027 NFL season with live and final scores, updated every 15 minutes via GitHub Actions.

## Subscribe

**URL:** `https://robtomlinson.github.io/nfl-calendar/nfl_2026.ics`

**iPhone:** Settings → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar → paste URL

## What's included

- All preseason, regular season, and playoff games
- Away @ Home team names in the event title
- Venue and city/stadium in the location field
- TV network in the event description
- Live scores updated to the event title during games
- Final scores once games end
- 🏈 all-day banner showing when the calendar was last refreshed

## How it works

- Data from ESPN's public API (no API key required)
- GitHub Actions runs every 15 minutes and regenerates the `.ics` file
- Hosted on GitHub Pages at the subscribe URL above
- All times stored as UTC — your calendar app converts to local time automatically

## Local development

```bash
pip install -r requirements.txt
python src/main.py
```

Generates `docs/nfl_2026.ics`.
