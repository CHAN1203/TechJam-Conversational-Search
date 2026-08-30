from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis.catalog_variants import add_catalog_variant_arguments, resolve_catalog_variants
from analysis.experiment_results import summary_delta
from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
from starter.agent import Agent


def _evaluate_catalog(catalog_path: str | Path, samples: list[dict]) -> dict:
    catalog_ids, categories, products = catalog_index(catalog_path)
    result = evaluate(Agent(catalog_path), samples, catalog_ids, categories, products)
    return {key: value for key, value in result.items() if key != "sessions"}


def run_catalog_evaluation(
    variants: dict[str, Path], samples: list[dict], manifest: dict | None = None
) -> dict:
    results = {
        name: _evaluate_catalog(path, samples)
        for name, path in variants.items()
    }
    if set(results) != {"official", "coverage_stress"}:
        return next(iter(results.values()))
    official = results["official"]
    stress = results["coverage_stress"]
    shared_scenarios = sorted(
        set(official["scenario_metrics"]) & set(stress["scenario_metrics"])
    )
    payload = {
        "schema_version": 1,
        "primary_catalog": "official",
        "catalogs": results,
        "deltas": {
            "direction": "coverage_stress_minus_official",
            "overall": summary_delta(official, stress),
            "scenario_metrics": {
                scenario: summary_delta(
                    official["scenario_metrics"][scenario],
                    stress["scenario_metrics"][scenario],
                )
                for scenario in shared_scenarios
            },
        },
    }
    if manifest is not None:
        payload["stress_manifest"] = manifest
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate official and coverage-stress catalogs")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--output", default="reports/experiments/coverage-stress-baseline.json")
    add_catalog_variant_arguments(parser)
    args = parser.parse_args()

    variants, _manifest = resolve_catalog_variants(
        args.catalog,
        args.dataset,
        args.catalog_mode,
        args.stress_catalog,
        args.stress_manifest,
        seed=args.stress_seed,
    )
    result = run_catalog_evaluation(variants, load_jsonl(args.dataset), manifest=_manifest)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
