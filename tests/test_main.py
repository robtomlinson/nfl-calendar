import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import main as app
from main import (
    SEQUENCE_BASE,
    SEQUENCE_VERSION,
    merge_game,
    migrate_sequences,
    needs_full_refresh,
    is_active_season,
    scoreboard_season_year,
)


def game(**overrides):
    data = {
        "id": "game-1",
        "date": "2026-09-13T17:00:00Z",
        "away_abbr": "NE",
        "away_name": "New England Patriots",
        "home_abbr": "SEA",
        "home_name": "Seattle Seahawks",
        "venue": "Lumen Field",
        "city": "Seattle",
        "state": "WA",
        "country": "USA",
        "networks": ["CBS"],
        "status": "STATUS_SCHEDULED",
        "status_detail": "Sun, September 13 at 1:00 PM EDT",
        "away_score": "0",
        "home_score": "0",
        "_sequence": 0,
    }
    data.update(overrides)
    return data


class SequenceTests(unittest.TestCase):
    def test_new_game_starts_in_current_sequence_range(self):
        merged = merge_game(None, game())
        self.assertEqual(merged["_sequence"], SEQUENCE_BASE)

    def test_meaningful_change_increments_sequence(self):
        existing = game(_sequence=SEQUENCE_BASE)
        incoming = game(status="STATUS_IN_PROGRESS", home_score="7")
        merged = merge_game(existing, incoming)
        self.assertEqual(merged["_sequence"], SEQUENCE_BASE + 1)

    def test_unchanged_game_keeps_sequence(self):
        existing = game(_sequence=SEQUENCE_BASE + 3)
        merged = merge_game(existing, game())
        self.assertEqual(merged["_sequence"], SEQUENCE_BASE + 3)

    def test_schedule_changes_increment_sequence(self):
        changes = {
            "date": "2026-09-14T00:20:00Z",
            "away_abbr": "BUF",
            "home_name": "Portland Seahawks",
            "venue": "Alternate Stadium",
            "networks": ["NBC"],
            "status_detail": "Flexed to Sunday Night Football",
        }

        for field, value in changes.items():
            with self.subTest(field=field):
                existing = game(_sequence=SEQUENCE_BASE)
                incoming = game(**{field: value})
                self.assertEqual(
                    merge_game(existing, incoming)["_sequence"], SEQUENCE_BASE + 1
                )

    def test_old_cache_is_migrated_only_once(self):
        cache = {"games": {"game-1": game(_sequence=1)}}
        migrate_sequences(cache)
        migrate_sequences(cache)
        self.assertEqual(cache["sequence_version"], SEQUENCE_VERSION)
        self.assertEqual(cache["games"]["game-1"]["_sequence"], SEQUENCE_BASE + 1)


class FullRefreshTests(unittest.TestCase):
    def test_refreshes_on_tuesday_in_a_new_iso_week(self):
        cache = {
            "fetched_at": "2026-08-25T12:00:00+00:00",
            "full_refresh_week": "2026-35",
        }
        tuesday = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)
        self.assertTrue(needs_full_refresh(cache, tuesday))

    def test_refreshes_only_once_during_tuesday(self):
        cache = {
            "fetched_at": "2026-09-01T07:05:00+00:00",
            "full_refresh_week": "2026-36",
        }
        later_tuesday = datetime(2026, 9, 1, 22, tzinfo=timezone.utc)
        self.assertFalse(needs_full_refresh(cache, later_tuesday))

    def test_does_not_refresh_early_on_monday(self):
        cache = {
            "fetched_at": "2026-08-25T12:00:00+00:00",
            "full_refresh_week": "2026-35",
        }
        monday = datetime(2026, 8, 31, 22, tzinfo=timezone.utc)
        self.assertFalse(needs_full_refresh(cache, monday))

    def test_utc_tuesday_does_not_start_refresh_while_central_time_is_monday(self):
        cache = {
            "fetched_at": "2026-08-25T12:00:00+00:00",
            "full_refresh_week": "2026-35",
        }
        monday_evening_central = datetime(2026, 9, 1, 2, tzinfo=timezone.utc)
        self.assertFalse(needs_full_refresh(cache, monday_evening_central))

    def test_overdue_refresh_runs_after_a_missed_tuesday(self):
        cache = {
            "fetched_at": "2026-08-25T12:00:00+00:00",
            "full_refresh_week": "2026-35",
        }
        wednesday = datetime(2026, 9, 2, 12, tzinfo=timezone.utc)
        self.assertTrue(needs_full_refresh(cache, wednesday))


class SeasonTests(unittest.TestCase):
    def test_reads_season_year_from_scoreboard(self):
        self.assertEqual(scoreboard_season_year({"season": {"year": 2027}}), 2027)

    def test_missing_season_year_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "season year"):
            scoreboard_season_year({})

    def test_active_season_months(self):
        self.assertTrue(is_active_season(datetime(2027, 2, 1, 12, tzinfo=timezone.utc)))
        self.assertTrue(is_active_season(datetime(2027, 8, 1, 12, tzinfo=timezone.utc)))
        self.assertFalse(is_active_season(datetime(2027, 6, 1, 12, tzinfo=timezone.utc)))

    @patch.object(app, "build_calendar")
    @patch.object(app, "save_cache")
    @patch.object(app, "fetch_full_season", return_value=[])
    @patch.object(app, "fetch_scoreboard", return_value={"season": {"year": 2027}})
    @patch.object(
        app,
        "load_cache",
        return_value={
            "season_year": 2026,
            "fetched_at": "2026-09-01T00:00:00+00:00",
            "games": {"old-game": game()},
        },
    )
    def test_empty_new_season_does_not_replace_published_calendar(
        self, _load, _scoreboard, _full_season, save_cache, build_calendar
    ):
        with self.assertRaisesRegex(RuntimeError, "refusing to replace"):
            app.main()

        save_cache.assert_not_called()
        build_calendar.assert_not_called()


class FailureHandlingTests(unittest.TestCase):
    @patch.object(app, "build_calendar")
    @patch.object(app, "save_cache")
    @patch.object(app, "fetch_scoreboard", side_effect=RuntimeError("ESPN unavailable"))
    @patch.object(app, "needs_full_refresh", return_value=False)
    @patch.object(app, "load_cache", return_value={"fetched_at": "2026-09-01T00:00:00+00:00"})
    def test_scoreboard_failure_prevents_publish(
        self, _load, _refresh, _scoreboard, save_cache, build_calendar
    ):
        with self.assertRaisesRegex(RuntimeError, "ESPN unavailable"):
            app.main()

        save_cache.assert_not_called()
        build_calendar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
