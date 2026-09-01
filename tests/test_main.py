import unittest
from unittest.mock import patch

import main as app
from main import SEQUENCE_BASE, SEQUENCE_VERSION, merge_game, migrate_sequences


def game(**overrides):
    data = {
        "id": "game-1",
        "status": "STATUS_SCHEDULED",
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

    def test_old_cache_is_migrated_only_once(self):
        cache = {"games": {"game-1": game(_sequence=1)}}
        migrate_sequences(cache)
        migrate_sequences(cache)
        self.assertEqual(cache["sequence_version"], SEQUENCE_VERSION)
        self.assertEqual(cache["games"]["game-1"]["_sequence"], SEQUENCE_BASE + 1)


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
