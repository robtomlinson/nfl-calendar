import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fetch import fetch_full_season, fetch_scoreboard, parse_game
from calendar_gen import build_calendar

CACHE_FILE = Path(__file__).parent.parent / "cache" / "schedule.json"
OUTPUT_FILE = Path(__file__).parent.parent / "docs" / "nfl.ics"
FULL_REFRESH_FALLBACK_DAYS = 8
SEQUENCE_VERSION = 2
SEQUENCE_BASE = 1_000_000
CALENDAR_FIELDS = (
    "date",
    "away_abbr",
    "away_name",
    "home_abbr",
    "home_name",
    "venue",
    "city",
    "state",
    "country",
    "networks",
    "status",
    "status_detail",
    "away_score",
    "home_score",
)
REFRESH_TIMEZONE = ZoneInfo("America/Chicago")


def load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(data: dict) -> None:
    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _refresh_week_key(value: datetime) -> str:
    iso_year, iso_week, _ = value.astimezone(REFRESH_TIMEZONE).isocalendar()
    return f"{iso_year}-{iso_week:02d}"


def is_active_season(now: datetime) -> bool:
    """The NFL plays preseason through postseason from August through February."""
    return now.astimezone(REFRESH_TIMEZONE).month in (1, 2, 8, 9, 10, 11, 12)


def scoreboard_season_year(scoreboard: dict) -> int:
    """Read ESPN's current NFL season year from a scoreboard response."""
    year = scoreboard.get("season", {}).get("year")
    if year is None:
        leagues = scoreboard.get("leagues", [])
        if leagues:
            year = leagues[0].get("season", {}).get("year")
    if year is None:
        raise ValueError("ESPN scoreboard did not include a season year")
    return int(year)


def needs_full_refresh(cache: dict, now: datetime | None = None) -> bool:
    """Refresh once each Tuesday, with an overdue fallback for missed runs."""
    now = now or datetime.now(tz=timezone.utc)
    fetched_at = cache.get("fetched_at")
    if not fetched_at:
        return True

    if cache.get("full_refresh_week") == _refresh_week_key(now):
        return False

    if now.astimezone(REFRESH_TIMEZONE).weekday() == 1:  # Tuesday
        return True

    last = datetime.fromisoformat(fetched_at)
    return now - last >= timedelta(days=FULL_REFRESH_FALLBACK_DAYS)


def migrate_sequences(cache: dict) -> None:
    """Move old event sequences into a new, monotonic range once."""
    if cache.get("sequence_version") == SEQUENCE_VERSION:
        return

    for game in cache.get("games", {}).values():
        game["_sequence"] = SEQUENCE_BASE + game.get("_sequence", 0)
    cache["sequence_version"] = SEQUENCE_VERSION


def merge_game(existing: dict | None, incoming: dict) -> dict:
    """Merge incoming game data into existing, bumping _sequence on meaningful changes."""
    if existing is None:
        return {**incoming, "_sequence": SEQUENCE_BASE}

    seq = existing.get("_sequence", 0)
    changed = any(existing.get(field) != incoming.get(field) for field in CALENDAR_FIELDS)
    merged = {**existing, **incoming}
    merged["_sequence"] = seq + 1 if changed else seq
    return merged


def main() -> None:
    now = datetime.now(tz=timezone.utc)
    cache = load_cache()
    migrate_sequences(cache)
    games_by_id: dict = cache.get("games", {})

    print("Fetching current scoreboard...")
    scoreboard = fetch_scoreboard()
    season_year = scoreboard_season_year(scoreboard)
    cached_season_year = cache.get("season_year")
    season_changed = cached_season_year is not None and cached_season_year != season_year

    if season_changed:
        print(f"NFL season changed from {cached_season_year} to {season_year}")
        games_by_id = {}
        cache.pop("fetched_at", None)
        cache.pop("full_refresh_week", None)
    cache["season_year"] = season_year

    if season_changed or needs_full_refresh(cache, now):
        print("Full season refresh...")
        events = fetch_full_season(season_year)
        if not events:
            raise RuntimeError(
                f"ESPN returned no games for the {season_year} NFL season; "
                "refusing to replace the published calendar"
            )
        for event in events:
            game = parse_game(event)
            games_by_id[game["id"]] = merge_game(games_by_id.get(game["id"]), game)
        cache["fetched_at"] = now.isoformat()
        cache["full_refresh_week"] = _refresh_week_key(now)
        print(f"Full refresh complete: {len(games_by_id)} games loaded")
    else:
        print(f"Cache is fresh (fetched {cache['fetched_at']}), skipping full refresh")

    live_events = scoreboard.get("events", [])
    live_count = 0
    for event in live_events:
        game = parse_game(event)
        games_by_id[game["id"]] = merge_game(games_by_id.get(game["id"]), game)
        if game["status"] == "STATUS_IN_PROGRESS":
            live_count += 1
    print(f"Scoreboard: {len(live_events)} games this week, {live_count} live")

    save_cache({**cache, "games": games_by_id})

    games = list(games_by_id.values())
    refresh_period = timedelta(minutes=15) if is_active_season(now) else timedelta(days=7)
    ics_bytes = build_calendar(games, now, season_year, refresh_period)

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_bytes(ics_bytes)

    final = sum(1 for g in games if g["status"] == "STATUS_FINAL")
    live = sum(1 for g in games if g["status"] == "STATUS_IN_PROGRESS")
    print(
        f"Generated {OUTPUT_FILE} — "
        f"{len(games)} total games, {live} live, {final} final"
    )


if __name__ == "__main__":
    main()
