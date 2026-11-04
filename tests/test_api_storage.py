import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from fastapi import HTTPException

import main


class OpusStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path = main.DB_PATH
        main.DB_PATH = os.path.join(self.temp.name, "test.sqlite3")
        os.environ["OPUS_INGEST_TOKEN"] = "test-token"

    def tearDown(self):
        main.DB_PATH = self.old_path
        self.temp.cleanup()

    def test_event_id_duplicate_is_idempotent(self):
        first = main.add_result(main.ResultIn(period="p1", outcome="BIG", event_id="event-1"), ingest_token="test-token")
        second = main.add_result(main.ResultIn(period="p1", outcome="BIG", event_id="event-1"), ingest_token="test-token")
        self.assertTrue(first["saved"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["id"], second["id"])

    def test_history_write_requires_configured_server_token(self):
        with patch.dict(os.environ, {"OPUS_INGEST_TOKEN": ""}):
            with self.assertRaises(HTTPException) as missing:
                main.add_result(main.ResultIn(period="p0", outcome="BIG"))
        self.assertEqual(missing.exception.status_code, 503)

        with patch.dict(os.environ, {"OPUS_INGEST_TOKEN": "server-secret"}):
            with self.assertRaises(HTTPException) as unauthorized:
                main.add_result(main.ResultIn(period="p1", outcome="BIG"), ingest_token=None)
            self.assertEqual(unauthorized.exception.status_code, 401)
            saved = main.add_result(
                main.ResultIn(period="p2", outcome="BIG"),
                ingest_token="server-secret",
            )
        self.assertTrue(saved["saved"])

    def test_provider_retains_raw_numeric_rows_without_guessing_size(self):
        records = [
            {"period": "p2", "outcome": None, "raw_result": 2, "payload_hash": "hash-p2"},
            {"period": "p1", "outcome": "BIG", "raw_result": 8, "payload_hash": "hash-p1"},
        ]
        first = main._persist_provider_history(records, "1m", history_order="oldest_first")
        second = main._persist_provider_history(records, "1m")
        self.assertEqual(first["raw_observations_saved"], 2)
        self.assertEqual(first["classified_results_saved"], 1)
        self.assertTrue(first["analysis_ingest_enabled"])
        self.assertEqual(first["history_order"], "oldest_first")
        self.assertEqual(second["raw_observations_saved"], 0)
        self.assertEqual(second["classified_results_saved"], 0)
        conn = main.db()
        try:
            raw_count = conn.execute(
                "SELECT COUNT(*) FROM provider_observations WHERE cycle_type='1m'"
            ).fetchone()[0]
            unclassified = conn.execute(
                "SELECT explicit_outcome,raw_result_json FROM provider_observations WHERE period='p2'"
            ).fetchone()
            analysis_count = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(raw_count, 2)
        self.assertIsNone(unclassified[0])
        self.assertEqual(unclassified[1], "2")
        self.assertEqual(analysis_count, 1)

    def test_opus_tool_includes_walk_forward_baseline(self):
        for index in range(25):
            main.add_result(main.ResultIn(
                period=f"p{index:03d}",
                outcome="BIG",
            ), ingest_token="test-token")
        result = main.run_tool("opus-1-0")
        self.assertEqual(result["window"], 30)
        self.assertEqual(result["backtest"]["method"], "expanding_window_majority_baseline")
        self.assertEqual(result["backtest"]["evaluated"], 5)
        self.assertEqual(result["backtest"]["accuracy_pct"], 100.0)

    def test_unknown_provider_history_order_archives_but_does_not_ingest(self):
        records = [
            {"period": "p2", "outcome": "SMALL", "raw_result": 2},
            {"period": "p1", "outcome": "BIG", "raw_result": 8},
        ]
        result = main._persist_provider_history(records, "1m", history_order="unknown")
        self.assertEqual(result["raw_observations_saved"], 2)
        self.assertEqual(result["classified_results_saved"], 0)
        self.assertFalse(result["analysis_ingest_enabled"])
        conn = main.db()
        try:
            raw_count = conn.execute("SELECT COUNT(*) FROM provider_observations").fetchone()[0]
            result_count = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(raw_count, 2)
        self.assertEqual(result_count, 0)

    def test_newest_first_provider_history_is_saved_oldest_first_for_analysis(self):
        records = [
            {"period": "p3", "outcome": "BIG"},
            {"period": "p2", "outcome": "SMALL"},
            {"period": "p1", "outcome": "BIG"},
        ]
        result = main._persist_provider_history(records, "1m", history_order="newest_first")
        self.assertEqual(result["classified_results_saved"], 3)
        rows = main.read_outcomes(10)
        self.assertEqual([row[0] for row in rows], ["p1", "p2", "p3"])
        self.assertEqual([row[1] for row in rows], ["BIG", "SMALL", "BIG"])

    def test_cycle_lengths(self):
        for seconds in (30, 60):
            result = main.current_cycle(seconds)
            self.assertEqual(result["cycle_seconds"], seconds)
            self.assertGreaterEqual(result["seconds_remaining"], 1)
            self.assertLessEqual(result["seconds_remaining"], seconds)

    def test_old_database_gets_provenance_columns(self):
        conn = sqlite3.connect(main.DB_PATH)
        conn.execute("CREATE TABLE results (id INTEGER PRIMARY KEY, period TEXT NOT NULL, outcome TEXT NOT NULL, created_at TEXT NOT NULL)")
        conn.execute("INSERT INTO results(period,outcome,created_at) VALUES('old','BIG','2026-01-01T00:00:00Z')")
        conn.commit()
        conn.close()
        conn = main.db()
        try:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(results)")}
            row = conn.execute("SELECT source,observed_at FROM results").fetchone()
        finally:
            conn.close()
        self.assertIn("event_id", columns)
        self.assertEqual(row, ("manual", "2026-01-01T00:00:00Z"))


if __name__ == "__main__":
    unittest.main()
