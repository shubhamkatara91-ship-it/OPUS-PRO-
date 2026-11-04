import asyncio
import os
import unittest
from unittest.mock import patch

from live_provider import (
    ProviderNotConfigured, ProviderError, _cycle_type,
    normalize_history, fetch_live_snapshot, _history_limit,
)


class LiveProviderTests(unittest.TestCase):
    def test_history_limit_supports_opus_500_window_and_clamps(self):
        self.assertEqual(_history_limit(20), 20)
        self.assertEqual(_history_limit(500), 500)
        self.assertEqual(_history_limit(900), 500)
        self.assertEqual(_history_limit(0), 1)

    def test_cycle_mapping_is_explicit(self):
        self.assertEqual(_cycle_type(30), "30s")
        self.assertEqual(_cycle_type(60), "1m")
        with self.assertRaises(ValueError):
            _cycle_type(45)

    def test_normalizes_only_explicit_big_small_fields(self):
        rows = normalize_history({
            "success": True,
            "data": {"results": [
                {"issue_number": "1002", "size": "small", "number": 2},
                {"issue_number": "1001", "number": 8},
            ]}
        })
        self.assertEqual(rows[0]["period"], "1002")
        self.assertEqual(rows[0]["outcome"], "SMALL")
        self.assertEqual(rows[0]["raw_result"], 2)
        self.assertIsNone(rows[1]["outcome"])
        self.assertEqual(rows[1]["period"], "1001")

    def test_missing_provider_url_is_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ProviderNotConfigured):
                asyncio.run(fetch_live_snapshot(60))

    def test_non_https_provider_is_rejected(self):
        with patch.dict(os.environ, {"PROVIDER_API_URL": "http://example.invalid"}, clear=True):
            with self.assertRaises(ProviderError):
                asyncio.run(fetch_live_snapshot(60))


if __name__ == "__main__":
    unittest.main()
