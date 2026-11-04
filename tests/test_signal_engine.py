import unittest

from signal_engine import analyze, walk_forward_backtest


class SignalEngineTests(unittest.TestCase):
    def test_empty_history_is_insufficient(self):
        result = analyze([])
        self.assertEqual(result["sample_size"], 0)
        self.assertEqual(result["status"], "insufficient_history")

    def test_observed_frequencies(self):
        result = analyze(["BIG", "SMALL", "BIG", "BIG"], min_samples=3)
        self.assertEqual(result["sample_size"], 4)
        self.assertEqual(result["observed_frequency_pct"], {"BIG": 75.0, "SMALL": 25.0})
        self.assertEqual(result["status"], "ready_for_research")

    def test_invalid_label_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze(["BIG", "UNKNOWN"])

    def test_walk_forward_never_trains_on_future_rows(self):
        result = walk_forward_backtest(["BIG", "BIG", "SMALL", "BIG", "SMALL"], min_train=2)
        self.assertEqual(result["method"], "expanding_window_majority_baseline")
        self.assertEqual(result["evaluated"], 3)


if __name__ == "__main__":
    unittest.main()
