from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis.coverage_stress import (
    DEFAULT_SEED,
    build_coverage_stress_catalog,
    manifest_is_current,
)


CATALOG_MODES = ("dual", "official", "stress")


def add_catalog_variant_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--catalog-mode", choices=CATALOG_MODES, default="dual")
    parser.add_argument(
        "--stress-catalog",
        default="data/generated/catalog-coverage-stress.jsonl",
    )
    parser.add_argument(
        "--stress-manifest",
        default="reports/experiments/coverage-stress-catalog.json",
    )
    parser.add_argument("--stress-seed", default=DEFAULT_SEED)


def resolve_catalog_variants(
    catalog_path: str | Path,
    dataset_path: str | Path,
    mode: str,
    stress_catalog_path: str | Path,
    manifest_path: str | Path,
    seed: str = DEFAULT_SEED,
) -> tuple[dict[str, Path], dict | None]:
    if mode not in CATALOG_MODES:
        raise ValueError(f"unsupported catalog mode: {mode}")
    official = Path(catalog_path)
    dataset = Path(dataset_path)
    if mode == "official":
        return {"official": official}, None

    stress = Path(stress_catalog_path)
    manifest_file = Path(manifest_path)
    if not manifest_is_current(official, dataset, stress, manifest_file, seed=seed):
        manifest = build_coverage_stress_catalog(
            official, dataset, stress, manifest_file, seed=seed
        )
    else:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

    if mode == "stress":
        return {"coverage_stress": stress}, manifest
    return {"official": official, "coverage_stress": stress}, manifest
