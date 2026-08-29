from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from analysis.catalog_variants import (
    add_catalog_variant_arguments,
    resolve_catalog_variants,
)


class CatalogVariantResolverTest(unittest.TestCase):
    def test_add_catalog_variant_arguments_uses_dual_defaults(self) -> None:
        parser = argparse.ArgumentParser()
        add_catalog_variant_arguments(parser)

        args = parser.parse_args([])

        self.assertEqual("dual", args.catalog_mode)
        self.assertEqual(
            "data/generated/catalog-coverage-stress.jsonl", args.stress_catalog
        )
        self.assertEqual(
            "reports/experiments/coverage-stress-catalog.json", args.stress_manifest
        )

    def _write_jsonl(self, path: Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )

    def _write_fixture(self, root: Path) -> tuple[Path, Path, Path, Path]:
        catalog_path = root / "catalog.jsonl"
        dataset_path = root / "samples.jsonl"
        stress_path = root / "generated.jsonl"
        manifest_path = root / "manifest.json"
        self._write_jsonl(catalog_path, [
            {"parent_asin": "A", "title": "alpha", "price": 10.0},
            {"parent_asin": "B", "title": "bravo", "price": 20.0},
        ])
        self._write_jsonl(dataset_path, [
            {"ground_truth": {"parent_asin": "A"}},
        ])
        return catalog_path, dataset_path, stress_path, manifest_path

    def test_official_mode_returns_source_without_building_stress_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog_path, dataset_path, stress_path, manifest_path = self._write_fixture(
                Path(directory)
            )

            official, manifest = resolve_catalog_variants(
                catalog_path=catalog_path,
                dataset_path=dataset_path,
                mode="official",
                stress_catalog_path=stress_path,
                manifest_path=manifest_path,
                seed="fixed",
            )

            self.assertEqual({"official": catalog_path}, official)
            self.assertIsNone(manifest)
            self.assertFalse(stress_path.exists())

    def test_dual_mode_builds_current_stress_catalog_after_official(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog_path, dataset_path, stress_path, manifest_path = self._write_fixture(
                Path(directory)
            )

            dual, manifest = resolve_catalog_variants(
                catalog_path=catalog_path,
                dataset_path=dataset_path,
                mode="dual",
                stress_catalog_path=stress_path,
                manifest_path=manifest_path,
                seed="fixed",
            )

            self.assertEqual({"official", "coverage_stress"}, set(dual))
            self.assertEqual(stress_path, dual["coverage_stress"])
            self.assertIsNotNone(manifest)

    def test_stress_mode_returns_only_generated_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog_path, dataset_path, stress_path, manifest_path = self._write_fixture(
                Path(directory)
            )

            variants, manifest = resolve_catalog_variants(
                catalog_path, dataset_path, "stress", stress_path, manifest_path, "fixed"
            )

            self.assertEqual({"coverage_stress": stress_path}, variants)
            self.assertIsNotNone(manifest)

    def test_cli_help_lists_every_build_argument(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "scripts.build_coverage_stress_catalog", "--help"],
            capture_output=True,
            text=True,
            check=True,
        )

        for option in ("--catalog", "--dataset", "--output", "--manifest", "--seed"):
            self.assertIn(option, result.stdout)


if __name__ == "__main__":
    unittest.main()
