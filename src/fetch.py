import time
import requests

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

SEASON_TYPES = {
    1: range(1, 5),   # preseason: weeks 1-4
    2: range(1, 19),  # regular season: weeks 1-18
    3: range(1, 6),   # playoffs: weeks 1-5 (Wild Card through Super Bowl)
}


def fetch_week(season_type: int, week: int, season_year: int = 2026) -> dict:
    url = f"{ESPN_BASE}/scoreboard"
    params = {"seasontype": season_type, "week": week, "dates": season_year}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_scoreboard() -> dict:
    """Fetch the current week's live scoreboard (no week/season params)."""
    resp = requests.get(f"{ESPN_BASE}/scoreboard", timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_full_season(year: int = 2026) -> list:
    """Fetch all events across preseason, regular season, and playoffs."""
    all_events = []
    for season_type, weeks in SEASON_TYPES.items():
        for week in weeks:
            try:
                data = fetch_week(season_type, week, year)
                events = data.get("events", [])
                if events:
                    all_events.extend(events)
                    print(f"  type={season_type} week={week}: {len(events)} games")
                time.sleep(1)
            except requests.HTTPError as e:
                print(f"  type={season_type} week={week}: HTTP {e.response.status_code}, skipping")
    return all_events


def parse_game(event: dict) -> dict:
    """Normalize an ESPN event object into a flat game dict."""
    competition = event["competitions"][0]

    home = next(c for c in competition["competitors"] if c["homeAway"] == "home")
    away = next(c for c in competition["competitors"] if c["homeAway"] == "away")

    venue = competition.get("venue", {})
    address = venue.get("address", {})

    networks = []
    for broadcast in competition.get("broadcasts", []):
        networks.extend(broadcast.get("names", []))

    status_obj = competition.get("status", {})
    status_type = status_obj.get("type", {})

    return {
        "id": event["id"],
        "date": event["date"],
        "away_abbr": away["team"]["abbreviation"],
        "away_name": away["team"]["displayName"],
        "home_abbr": home["team"]["abbreviation"],
        "home_name": home["team"]["displayName"],
        "venue": venue.get("fullName", ""),
        "city": address.get("city", ""),
        "state": address.get("state", ""),
        "country": address.get("country", "US"),
        "networks": networks,
        "status": status_type.get("name", "STATUS_SCHEDULED"),
        "status_detail": status_obj.get("detail", ""),
        "away_score": away.get("score", ""),
        "home_score": home.get("score", ""),
        "_sequence": 0,
    }
