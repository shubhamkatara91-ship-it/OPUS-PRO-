import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import main


class OpusStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path = main.DB_PATH
        main.DB_PATH = os.path.join(self.temp.name, "test.sqlite3")
        os.environ.pop("OPUS_INGEST_TOKEN", None)

    def tearDown(self):
        main.DB_PATH = self.old_path
        self.temp.cleanup()

    def test_event_id_duplicate_is_idempotent(self):
        first = main.add_result(main.ResultIn(period="p1", outcome="BIG", event_id="event-1"))
        second = main.add_result(main.ResultIn(period="p1", outcome="BIG", event_id="event-1"))
        self.assertTrue(first["saved"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["id"], second["id"])

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
