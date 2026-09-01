# Current NFL Season iCal Calendar

Subscribable calendar for the current NFL season with live and final scores. Subscribe once and keep the same URL across future seasons.

## Subscribe

**URL:** `https://robtomlinson.github.io/nfl-calendar/nfl.ics`

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
- During the NFL season, GitHub Actions updates the calendar every 15 minutes
- During the offseason, the calendar updates once each Tuesday
- The season year is detected automatically from ESPN
- Hosted on GitHub Pages at the subscribe URL above
- All times stored as UTC — your calendar app converts to local time automatically

## Local development

```bash
pip install -r requirements.txt
python src/main.py
```

Generates `docs/nfl.ics`.
