from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from analysis.coverage_stress import (
    FieldMaskPlan,
    apply_masks_to_product,
    build_coverage_stress_catalog,
    file_sha256,
    manifest_is_current,
    plan_field_masks,
)


class CoverageStressPlanTest(unittest.TestCase):
    def setUp(self) -> None:
        self.products = [
            {
                "parent_asin": "A",
                "price": 10.0,
                "features": ["cotton"],
                "description": ["alpha"],
                "details": {"color": "red"},
                "store": "one",
            },
            {
                "parent_asin": "B",
                "price": 20.0,
                "features": ["wool"],
                "description": [],
                "details": {"color": "blue"},
                "store": "two",
            },
            {
                "parent_asin": "C",
                "price": None,
                "features": ["silk"],
                "description": ["charlie"],
                "details": {},
                "store": None,
            },
            {
                "parent_asin": "D",
                "price": None,
                "features": [],
                "description": ["delta"],
                "details": {"color": "black"},
                "store": "four",
            },
        ]

    def test_plan_masks_only_overcovered_target_fields(self) -> None:
        plans = plan_field_masks(
            self.products,
            target_ids=("A", "B"),
            fields=("price", "features", "description", "details", "store"),
            seed="fixed",
        )

        self.assertEqual(1, plans["price"].desired_target_present)
        self.assertEqual(2, plans["price"].original_target_present)
        self.assertEqual(1, len(plans["price"].masked_ids))
        self.assertEqual(frozenset({"A"}), plans["price"].masked_ids)
        self.assertEqual(2, plans["description"].desired_target_present)
        self.assertEqual(1, plans["description"].original_target_present)
        self.assertEqual(0, len(plans["description"].masked_ids))
        self.assertEqual(1, plans["description"].unfillable_shortfall)

    def test_apply_masks_never_fills_a_missing_field(self) -> None:
        plans = plan_field_masks(
            self.products,
            target_ids=("A", "B"),
            fields=("price", "description"),
            seed="fixed",
        )
        masked = [apply_masks_to_product(product, plans) for product in self.products]

        self.assertEqual([], masked[1]["description"])
        self.assertEqual(["charlie"], masked[2]["description"])
        self.assertEqual(["delta"], masked[3]["description"])
        self.assertEqual(1, sum(row["price"] is not None for row in masked[:2]))

        details_plan = FieldMaskPlan(
            field="details",
            catalog_present=4,
            catalog_coverage=1.0,
            desired_target_present=1,
            original_target_present=1,
            masked_ids=frozenset({"A"}),
            unfillable_shortfall=0,
        )
        self.assertEqual({}, apply_masks_to_product(self.products[0], {"details": details_plan})["details"])

    def test_same_seed_produces_the_same_mask_ids(self) -> None:
        first = plan_field_masks(self.products, ("A", "B"), ("price",), "fixed")
        second = plan_field_masks(self.products, ("B", "A"), ("price",), "fixed")
        self.assertEqual(first["price"].masked_ids, second["price"].masked_ids)

    def test_rejects_duplicate_target_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be distinct"):
            plan_field_masks(self.products, ("A", "A"), ("price",), "fixed")

    def test_rejects_missing_target_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing from catalog"):
            plan_field_masks(self.products, ("A", "missing"), ("price",), "fixed")

    def test_rejects_duplicate_catalog_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate catalog parent_asin"):
            plan_field_masks([self.products[0], self.products[0]], ("A",), ("price",), "fixed")


class CoverageStressBuildTest(unittest.TestCase):
    fields = ("price", "features", "description", "details", "store")

    def _write_jsonl(self, path: Path, rows: list[dict]) -> None:
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")

    def _write_fixture(self, root: Path) -> tuple[Path, Path, Path, Path]:
        catalog_path = root / "catalog.jsonl"
        dataset_path = root / "samples.jsonl"
        output_path = root / "generated.jsonl"
        manifest_path = root / "manifest.json"
        self._write_jsonl(catalog_path, [
            {"parent_asin": "A", "price": 10.0, "features": ["cotton"], "description": ["alpha"], "details": {"color": "red"}, "store": "one"},
            {"parent_asin": "B", "price": 20.0, "features": ["wool"], "description": [], "details": {"color": "blue"}, "store": "two"},
            {"parent_asin": "C", "price": None, "features": ["silk"], "description": ["charlie"], "details": {}, "store": None},
            {"parent_asin": "D", "price": None, "features": [], "description": ["delta"], "details": {"color": "black"}, "store": "four"},
        ])
        self._write_jsonl(dataset_path, [
            {"ground_truth": {"parent_asin": "A"}},
            {"ground_truth": {"parent_asin": "B"}},
        ])
        return catalog_path, dataset_path, output_path, manifest_path

    def test_builds_a_validated_catalog_and_aggregate_manifest(self) -> None:
        products = [
            {"parent_asin": "A", "price": 10.0, "features": ["cotton"], "description": ["alpha"], "details": {"color": "red"}, "store": "one"},
            {"parent_asin": "B", "price": 20.0, "features": ["wool"], "description": [], "details": {"color": "blue"}, "store": "two"},
            {"parent_asin": "C", "price": None, "features": ["silk"], "description": ["charlie"], "details": {}, "store": None},
            {"parent_asin": "D", "price": None, "features": [], "description": ["delta"], "details": {"color": "black"}, "store": "four"},
        ]
        samples = [
            {"ground_truth": {"parent_asin": "A"}},
            {"ground_truth": {"parent_asin": "B"}},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.jsonl"
            dataset_path = root / "samples.jsonl"
            output_path = root / "generated.jsonl"
            manifest_path = root / "manifest.json"
            self._write_jsonl(catalog_path, products)
            self._write_jsonl(dataset_path, samples)

            manifest = build_coverage_stress_catalog(
                source_catalog=catalog_path,
                dataset_path=dataset_path,
                output_catalog=output_path,
                manifest_path=manifest_path,
                fields=self.fields,
                seed="fixed",
            )

            self.assertEqual(4, manifest["catalog_row_count"])
            self.assertEqual(2, manifest["session_count"])
            self.assertEqual(2, manifest["distinct_target_count"])
            self.assertEqual(1, manifest["fields"]["price"]["stress_target_present"])
            self.assertEqual(1, manifest["fields"]["description"]["unfillable_shortfall"])
            self.assertTrue(output_path.exists())
            self.assertTrue(manifest_path.exists())
            self.assertTrue(manifest_is_current(
                source_catalog=catalog_path,
                dataset_path=dataset_path,
                output_catalog=output_path,
                manifest_path=manifest_path,
                seed="fixed",
                fields=self.fields,
            ))

            source_rows = [json.loads(line) for line in catalog_path.read_text(encoding="utf-8").splitlines()]
            generated = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["parent_asin"] for row in source_rows], [row["parent_asin"] for row in generated])
            self.assertEqual(source_rows[2], generated[2])
            self.assertEqual(source_rows[3], generated[3])
            plans = plan_field_masks(source_rows, ("A", "B"), self.fields, "fixed")
            for source, result in zip(source_rows, generated):
                changed_fields = {
                    field for field in set(source) | set(result)
                    if source.get(field) != result.get(field)
                }
                expected_changes = {
                    field for field, plan in plans.items()
                    if source["parent_asin"] in plan.masked_ids
                }
                self.assertEqual(expected_changes, changed_fields)

    def test_rebuild_is_deterministic_detects_staleness_and_preserves_output_on_validation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog_path, dataset_path, output_path, manifest_path = self._write_fixture(Path(directory))
            build_coverage_stress_catalog(
                catalog_path, dataset_path, output_path, manifest_path, self.fields, "fixed"
            )
            first_hash = file_sha256(output_path)
            build_coverage_stress_catalog(
                catalog_path, dataset_path, output_path, manifest_path, self.fields, "fixed"
            )
            self.assertEqual(first_hash, file_sha256(output_path))

            samples = [json.loads(line) for line in dataset_path.read_text(encoding="utf-8").splitlines()]
            samples[0]["query"] = "changed but valid"
            self._write_jsonl(dataset_path, samples)
            self.assertFalse(manifest_is_current(
                catalog_path, dataset_path, output_path, manifest_path, "fixed", self.fields
            ))
            build_coverage_stress_catalog(
                catalog_path, dataset_path, output_path, manifest_path, self.fields, "fixed"
            )
            self.assertTrue(manifest_is_current(
                catalog_path, dataset_path, output_path, manifest_path, "fixed", self.fields
            ))

            valid_hash = file_sha256(output_path)
            with mock.patch(
                "analysis.coverage_stress._validate_generated_catalog",
                side_effect=ValueError("validation failed"),
            ):
                with self.assertRaisesRegex(ValueError, "validation failed"):
                    build_coverage_stress_catalog(
                        catalog_path, dataset_path, output_path, manifest_path, self.fields, "fixed"
                    )
            self.assertEqual(valid_hash, file_sha256(output_path))


if __name__ == "__main__":
    unittest.main()
