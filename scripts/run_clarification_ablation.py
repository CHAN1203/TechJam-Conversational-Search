from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

from analysis.catalog_variants import add_catalog_variant_arguments, resolve_catalog_variants
from analysis.experiment_results import summary_delta, summarize_sessions
from analysis.experiment_split import stratified_split
from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
from starter.agent import Agent


DEFAULT_POLICIES = ("fixed", "profile", "candidate")
DEFAULT_SEED = "techjam-clarification-v1"


def _stratum_counts(samples: list[dict]) -> dict[str, int]:
    counts = Counter(
        f"{sample.get('scenario_type', '')}/{sample.get('difficulty_bucket', '')}"
        for sample in samples
    )
    return dict(sorted(counts.items()))


def run_ablation(
    catalog_path: str | Path,
    samples: list[dict],
    policies: tuple[str, ...] = DEFAULT_POLICIES,
    validation_size: int = 80,
    seed: str = DEFAULT_SEED,
) -> dict:
    development, validation = stratified_split(samples, validation_size, seed)
    development_ids = {str(sample["sample_id"]) for sample in development}
    validation_ids = {str(sample["sample_id"]) for sample in validation}
    catalog_ids, categories, products = catalog_index(catalog_path)

    policy_results: dict[str, dict] = {}
    for policy in policies:
        started = time.perf_counter()
        result = evaluate(
            Agent(catalog_path, clarification_policy=policy),
            samples,
            catalog_ids,
            categories,
            products,
        )
        sessions = result["sessions"]
        policy_results[policy] = {
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "full": summarize_sessions(sessions),
            "development": summarize_sessions([
                session for session in sessions
                if str(session["sample_id"]) in development_ids
            ]),
            "validation": summarize_sessions([
                session for session in sessions
                if str(session["sample_id"]) in validation_ids
            ]),
        }

    return {
        "split": {
            "seed": seed,
            "development_count": len(development),
            "validation_count": len(validation),
            "development_strata": _stratum_counts(development),
            "validation_strata": _stratum_counts(validation),
        },
        "policies": policy_results,
    }


def run_ablation_variants(
    variants: dict[str, Path],
    samples: list[dict],
    policies: tuple[str, ...] = DEFAULT_POLICIES,
    validation_size: int = 80,
    seed: str = DEFAULT_SEED,
) -> dict:
    results = {
        name: run_ablation(path, samples, policies, validation_size, seed)
        for name, path in variants.items()
    }
    if set(results) != {"official", "coverage_stress"}:
        return next(iter(results.values()))
    official = results["official"]["policies"]
    stress = results["coverage_stress"]["policies"]
    return {
        "schema_version": 1,
        "catalogs": results,
        "delta_direction": "coverage_stress_minus_official",
        "deltas": {
            policy: {
                split: summary_delta(official[policy][split], stress[policy][split])
                for split in ("full", "development", "validation")
            }
            for policy in policies
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare clarification policies on a fixed split")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument(
        "--output",
        default="reports/experiments/clarification-ablation.json",
    )
    parser.add_argument("--validation-size", type=int, default=80)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--policies", nargs="+", default=list(DEFAULT_POLICIES))
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
    result = run_ablation_variants(
        variants,
        load_jsonl(args.dataset),
        policies=tuple(args.policies),
        validation_size=args.validation_size,
        seed=args.seed,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
