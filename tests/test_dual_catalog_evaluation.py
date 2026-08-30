from __future__ import annotations

import tempfile
import json
import unittest
from pathlib import Path

from analysis.experiment_results import summary_delta
from scripts.run_dual_catalog_evaluation import run_catalog_evaluation


class DualCatalogEvaluationTest(unittest.TestCase):
    def test_dual_payload_is_aggregate_and_reports_stress_delta(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            official = Path(directory) / "official.jsonl"
            stress = Path(directory) / "stress.jsonl"
            products = [
                {"parent_asin": "A", "title": "blue shoe", "features": ["blue"],
                 "categories": ["Shoes"], "description": ["walking"]},
                {"parent_asin": "B", "title": "red boot", "features": ["red"],
                 "categories": ["Shoes"], "description": ["walking"]},
            ]
            official.write_text("".join(json.dumps(row) + "\n" for row in products), encoding="utf-8")
            masked = [{**products[0], "title": "shoe", "features": []},
                      {**products[1], "title": "blue shoe", "features": ["blue"]}]
            stress.write_text("".join(json.dumps(row) + "\n" for row in masked), encoding="utf-8")
            samples = [{"sample_id": "s1", "scenario_type": "buying", "user_profile": {},
                        "ground_truth": {"parent_asin": "A"},
                        "intent_card": {"target_category": "blue shoe", "hard_constraints": ["blue"],
                                        "soft_preferences": []}, "behavior": {}}]
            payload = run_catalog_evaluation(
                {"official": official, "coverage_stress": stress}, samples,
                manifest={"session_count": 1, "fields": {"title": {"masked": 1}}},
            )
            official_summary = payload["catalogs"]["official"]
            stress_summary = payload["catalogs"]["coverage_stress"]
            self.assertEqual({"official", "coverage_stress"}, set(payload["catalogs"]))
            self.assertEqual("official", payload["primary_catalog"])
            self.assertEqual(1, payload["stress_manifest"]["session_count"])
            self.assertNotIn("sessions", payload["catalogs"]["official"])
            self.assertNotIn("sessions", payload["catalogs"]["coverage_stress"])
            self.assertNotEqual(official_summary["mrr"], stress_summary["mrr"])
            self.assertEqual(summary_delta(official_summary, stress_summary), payload["deltas"]["overall"])
            self.assertEqual({"buying"}, set(payload["deltas"]["scenario_metrics"]))

    def test_single_catalog_mode_preserves_legacy_aggregate_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "catalog.jsonl"
            catalog.write_text('{"parent_asin":"A","title":"blue shoe","categories":["Shoes"]}\n', encoding="utf-8")
            sample = {"sample_id": "s1", "scenario_type": "buying", "user_profile": {},
                      "ground_truth": {"parent_asin": "A"},
                      "intent_card": {"target_category": "blue shoe", "hard_constraints": ["blue"],
                                      "soft_preferences": []}, "behavior": {}}
            for name in ("official", "coverage_stress"):
                payload = run_catalog_evaluation({name: catalog}, [sample])
                self.assertIn("sample_count", payload)
                self.assertNotIn("catalogs", payload)
                self.assertNotIn("sessions", payload)


if __name__ == "__main__":
    unittest.main()
