from __future__ import annotations

import unittest

from analysis.bm25_diagnostics import rank_of, summarize_ranks


class Bm25DiagnosticsTest(unittest.TestCase):
    def test_rank_of_returns_one_based_rank_or_none(self) -> None:
        self.assertEqual(rank_of("B", ["A", "B", "C"]), 2)
        self.assertIsNone(rank_of("Z", ["A", "B", "C"]))

    def test_summarize_ranks_reports_literal_cutoff_rates_by_scenario(self) -> None:
        records = [
            {"scenario_type": "buying", "rank": 1},
            {"scenario_type": "buying", "rank": 25},
            {"scenario_type": "browsing", "rank": None},
            {"scenario_type": "browsing", "rank": 75},
        ]
        self.assertEqual(summarize_ranks(records, (10, 50, 100)), {
            "sample_count": 4,
            "recall": {"10": 0.25, "50": 0.5, "100": 0.75},
            "scenario_recall": {
                "browsing": {
                    "sample_count": 2,
                    "recall": {"10": 0.0, "50": 0.0, "100": 0.5},
                },
                "buying": {
                    "sample_count": 2,
                    "recall": {"10": 0.5, "50": 1.0, "100": 1.0},
                },
            },
        })


if __name__ == "__main__":
    unittest.main()
