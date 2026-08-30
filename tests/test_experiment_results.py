from __future__ import annotations

import unittest

from analysis.experiment_results import summarize_sessions, summary_delta


class ExperimentResultsTest(unittest.TestCase):
    def test_summary_delta_reports_only_core_metrics(self) -> None:
        official = {
            "sample_count": 2, "hit_rate_at_10": 0.5, "mrr": 0.25,
            "mttc": 7.0, "efficiency": 0.4,
            "recommended_technical_score": 0.405,
        }
        stress = {
            "sample_count": 2, "hit_rate_at_10": 0.25, "mrr": 0.125,
            "mttc": 9.0, "efficiency": 0.2,
            "recommended_technical_score": 0.2025,
        }
        self.assertEqual(
            {"hit_rate_at_10": -0.25, "mrr": -0.125, "mttc": 2.0,
             "efficiency": -0.2, "recommended_technical_score": -0.2025},
            summary_delta(official, stress),
        )

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
