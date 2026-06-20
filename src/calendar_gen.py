from datetime import datetime, timedelta, timezone

from icalendar import Calendar, Event, vDuration, vText


def _location(game: dict) -> str:
    country = (game.get("country") or "US").upper()
    city = game.get("city", "")
    state = game.get("state", "")
    venue = game.get("venue", "")

    if country not in ("US", "USA"):
        geo = f"{city}, {country}" if city else country
    else:
        geo = f"{city}, {state}" if city and state else city

    return f"{venue}, {geo}" if venue and geo else venue or geo


def _summary(game: dict) -> str:
    away = game["away_abbr"]
    home = game["home_abbr"]
    status = game["status"]

    if status == "STATUS_FINAL":
        return f"{away} {game['away_score']} @ {home} {game['home_score']} (Final)"
    if status == "STATUS_IN_PROGRESS":
        return f"{away} {game['away_score']} @ {home} {game['home_score']} (Live)"
    return f"{away} @ {home}"


def _description(game: dict) -> str:
    lines = [
        f"{game['away_name']} at {game['home_name']}",
        f"Venue: {_location(game)}",
    ]
    if game["networks"]:
        lines.append(f"TV: {', '.join(game['networks'])}")
    if game["status"] == "STATUS_FINAL":
        lines.append(
            f"Final: {game['away_abbr']} {game['away_score']} - "
            f"{game['home_abbr']} {game['home_score']}"
        )
    elif game["status"] == "STATUS_IN_PROGRESS":
        lines.append(
            f"Live: {game['away_abbr']} {game['away_score']} - "
            f"{game['home_abbr']} {game['home_score']}"
        )
    if game.get("status_detail"):
        lines.append(game["status_detail"])
    return "\n".join(lines)


def game_to_event(game: dict, now: datetime) -> Event:
    event = Event()

    event.add("uid", f"nfl-2026-{game['id']}@espn.com")
    event.add("sequence", game.get("_sequence", 0))
    event.add("dtstamp", now)
    event.add("last-modified", now)

    start = datetime.fromisoformat(game["date"].replace("Z", "+00:00"))
    end = start + timedelta(hours=3, minutes=30)
    event.add("dtstart", start)
    event.add("dtend", end)

    event.add("summary", _summary(game))
    event.add("location", _location(game))
    event.add("description", _description(game))
    event.add("transp", "OPAQUE")

    return event


def last_updated_event(updated_at: datetime) -> Event:
    event = Event()

    event.add("uid", "nfl-2026-last-updated@espn.com")

    epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
    sequence = int((updated_at - epoch).total_seconds() // 900)
    event.add("sequence", sequence)

    event.add("dtstamp", updated_at)
    event.add("last-modified", updated_at)

    today = updated_at.date()
    event.add("dtstart", today)
    event.add("dtend", today + timedelta(days=1))

    hour = updated_at.hour % 12 or 12
    formatted = f"{updated_at.strftime('%b')} {updated_at.day} {hour}:{updated_at.strftime('%M')} {updated_at.strftime('%p')} UTC"
    event.add("summary", f"\U0001f3c8 Updated {formatted}")
    event.add("transp", "TRANSPARENT")

    return event


def build_calendar(games: list, updated_at: datetime) -> bytes:
    cal = Calendar()
    cal.add("prodid", "-//NFL 2026 Calendar//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", "NFL 2026-2027")
    cal.add("x-wr-caldesc", "NFL 2026-2027 Schedule with Live Scores")
    refresh = vDuration(timedelta(minutes=15))
    refresh.params["VALUE"] = "DURATION"
    cal.add("refresh-interval", refresh)
    cal.add("x-published-ttl", vText("PT15M"))

    for game in sorted(games, key=lambda g: g["date"]):
        cal.add_component(game_to_event(game, updated_at))

    cal.add_component(last_updated_event(updated_at))

    return cal.to_ical()
