from __future__ import annotations

import unittest

from analysis.experiment_results import summarize_sessions


class ExperimentResultsTest(unittest.TestCase):
    def test_summarize_sessions_calculates_composite_and_scenarios(self) -> None:
        sessions = [
            {
                "sample_id": "hit",
                "scenario_type": "buying",
                "hit": True,
                "first_hit_turn": 3,
                "best_rank": 2,
                "reciprocal_rank": 0.5,
            },
            {
                "sample_id": "miss",
                "scenario_type": "browsing",
                "hit": False,
                "first_hit_turn": None,
                "best_rank": None,
                "reciprocal_rank": 0.0,
            },
        ]

        summary = summarize_sessions(sessions)

        self.assertEqual(0.5, summary["hit_rate_at_10"])
        self.assertEqual(0.25, summary["mrr"])
        self.assertEqual(7.0, summary["mttc"])
        self.assertEqual(0.4, summary["efficiency"])
        self.assertEqual(0.405, summary["recommended_technical_score"])
        self.assertEqual(1.0, summary["scenario_metrics"]["buying"]["hit_rate_at_10"])
        self.assertEqual(0.0, summary["scenario_metrics"]["browsing"]["hit_rate_at_10"])


if __name__ == "__main__":
    unittest.main()
