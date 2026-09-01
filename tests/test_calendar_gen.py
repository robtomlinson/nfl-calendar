import unittest
from datetime import datetime, timezone

from icalendar import Calendar

from calendar_gen import build_calendar
from main import SEQUENCE_BASE


def game(status="STATUS_SCHEDULED", sequence=SEQUENCE_BASE):
    return {
        "id": "401000001",
        "date": "2026-09-10T00:20:00Z",
        "away_abbr": "NE",
        "away_name": "New England Patriots",
        "home_abbr": "SEA",
        "home_name": "Seattle Seahawks",
        "venue": "Lumen Field",
        "city": "Seattle",
        "state": "WA",
        "country": "USA",
        "networks": ["NBC"],
        "status": status,
        "status_detail": "Final",
        "away_score": "21",
        "home_score": "24",
        "_sequence": sequence,
    }


class CalendarTests(unittest.TestCase):
    def test_final_score_and_sequence_are_published(self):
        now = datetime(2026, 9, 10, 4, tzinfo=timezone.utc)
        calendar = Calendar.from_ical(
            build_calendar([game(status="STATUS_FINAL", sequence=SEQUENCE_BASE + 2)], now)
        )
        event = next(
            component
            for component in calendar.walk("VEVENT")
            if str(component["UID"]).startswith("nfl-2026-401000001")
        )
        self.assertEqual(str(event["SUMMARY"]), "NE 21 @ SEA 24 (Final)")
        self.assertEqual(int(event["SEQUENCE"]), SEQUENCE_BASE + 2)


if __name__ == "__main__":
    unittest.main()
