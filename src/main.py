import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fetch import fetch_full_season, fetch_scoreboard, parse_game
from calendar_gen import build_calendar

CACHE_FILE = Path(__file__).parent.parent / "cache" / "schedule.json"
OUTPUT_FILE = Path(__file__).parent.parent / "docs" / "nfl_2026.ics"
FULL_REFRESH_DAYS = 7


def load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(data: dict) -> None:
    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def needs_full_refresh(cache: dict) -> bool:
    fetched_at = cache.get("fetched_at")
    if not fetched_at:
        return True
    last = datetime.fromisoformat(fetched_at)
    age_days = (datetime.now(tz=timezone.utc) - last).days
    return age_days >= FULL_REFRESH_DAYS


def merge_game(existing: dict | None, incoming: dict) -> dict:
    """Merge incoming game data into existing, bumping _sequence on meaningful changes."""
    if existing is None:
        return incoming

    seq = existing.get("_sequence", 0)
    changed = (
        existing.get("status") != incoming.get("status")
        or existing.get("away_score") != incoming.get("away_score")
        or existing.get("home_score") != incoming.get("home_score")
    )
    merged = {**existing, **incoming}
    merged["_sequence"] = seq + 1 if changed else seq
    return merged


def main() -> None:
    now = datetime.now(tz=timezone.utc)
    cache = load_cache()
    games_by_id: dict = cache.get("games", {})

    if needs_full_refresh(cache):
        print("Full season refresh...")
        events = fetch_full_season()
        for event in events:
            game = parse_game(event)
            games_by_id[game["id"]] = merge_game(games_by_id.get(game["id"]), game)
        cache["fetched_at"] = now.isoformat()
        print(f"Full refresh complete: {len(games_by_id)} games loaded")
    else:
        print(f"Cache is fresh (fetched {cache['fetched_at']}), skipping full refresh")

    print("Fetching live scoreboard...")
    try:
        scoreboard = fetch_scoreboard()
        live_events = scoreboard.get("events", [])
        live_count = 0
        for event in live_events:
            game = parse_game(event)
            games_by_id[game["id"]] = merge_game(games_by_id.get(game["id"]), game)
            if game["status"] == "STATUS_IN_PROGRESS":
                live_count += 1
        print(f"Scoreboard: {len(live_events)} games this week, {live_count} live")
    except Exception as e:
        print(f"Scoreboard fetch failed: {e}", file=sys.stderr)

    save_cache({**cache, "games": games_by_id})

    games = list(games_by_id.values())
    ics_bytes = build_calendar(games, now)

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
