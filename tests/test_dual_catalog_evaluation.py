from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analysis.experiment_results import summary_delta
from scripts.run_dual_catalog_evaluation import run_catalog_evaluation


class DualCatalogEvaluationTest(unittest.TestCase):
    def test_dual_payload_is_aggregate_and_reports_stress_delta(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            official = Path(directory) / "official.jsonl"
            stress = Path(directory) / "stress.jsonl"
            official.write_text('{"parent_asin":"A","title":"blue shoe"}\n', encoding="utf-8")
            stress.write_text('{"parent_asin":"A","title":"shoe"}\n', encoding="utf-8")
            samples = [{"sample_id": "s1", "scenario_type": "buying"}]
            official_result = {
                "sample_count": 1, "hit_rate_at_10": 1.0, "mrr": 1.0,
                "mttc": 1.0, "efficiency": 1.0,
                "recommended_technical_score": 1.0,
                "scenario_metrics": {"buying": {"sample_count": 1, "hit_rate_at_10": 1.0,
                    "mrr": 1.0, "mttc": 1.0}}, "sessions": [{"sample_id": "s1"}],
            }
            stress_result = {**official_result, "hit_rate_at_10": 0.0, "mrr": 0.0,
                "mttc": 11.0, "efficiency": 0.0, "recommended_technical_score": 0.0,
                "scenario_metrics": {"buying": {"sample_count": 1, "hit_rate_at_10": 0.0,
                    "mrr": 0.0, "mttc": 11.0}}}
            with patch("scripts.run_dual_catalog_evaluation._evaluate_catalog",
                       side_effect=[{k: v for k, v in official_result.items() if k != "sessions"},
                                    {k: v for k, v in stress_result.items() if k != "sessions"}]):
                payload = run_catalog_evaluation({"official": official, "coverage_stress": stress}, samples)
            self.assertEqual({"official", "coverage_stress"}, set(payload["catalogs"]))
            self.assertNotIn("sessions", payload["catalogs"]["official"])
            self.assertEqual(summary_delta(official_result, stress_result), payload["deltas"]["overall"])
            self.assertEqual({"buying"}, set(payload["deltas"]["scenario_metrics"]))

    def test_single_catalog_mode_preserves_legacy_aggregate_shape(self) -> None:
        result = {"sample_count": 1, "scenario_metrics": {}}
        with patch("scripts.run_dual_catalog_evaluation._evaluate_catalog", return_value=result):
            payload = run_catalog_evaluation({"official": Path("official.jsonl")}, [])
        self.assertEqual(result, payload)
        self.assertNotIn("catalogs", payload)


if __name__ == "__main__":
    unittest.main()
