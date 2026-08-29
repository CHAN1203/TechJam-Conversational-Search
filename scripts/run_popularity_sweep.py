from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis.catalog_variants import add_catalog_variant_arguments, resolve_catalog_variants
from analysis.experiment_results import summary_delta, summarize_sessions
from analysis.experiment_split import stratified_split
from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
from starter.agent import Agent


DEFAULT_WEIGHTS = (0.0, 0.15, 0.3, 0.5, 0.8, 1.2)
DEFAULT_SEED = "techjam-clarification-v1"


def run_popularity_sweep(
    catalog_path: str | Path,
    samples: list[dict],
    weights: tuple[float, ...] = DEFAULT_WEIGHTS,
    validation_size: int = 80,
    seed: str = DEFAULT_SEED,
) -> dict:
    development, validation = stratified_split(samples, validation_size, seed)
    development_ids = {str(s["sample_id"]) for s in development}
    validation_ids = {str(s["sample_id"]) for s in validation}
    catalog_ids, categories, products = catalog_index(catalog_path)

    difficulty = {
        str(sample["sample_id"]): str(sample.get("difficulty_bucket", "unknown"))
        for sample in samples
    }
    buckets = sorted(set(difficulty.values()))

    results: dict[str, dict] = {}
    for weight in weights:
        sessions = evaluate(
            Agent(catalog_path, popularity_weight=weight),
            samples, catalog_ids, categories, products,
        )["sessions"]
        results[f"{weight:g}"] = {
            "full": summarize_sessions(sessions),
            "development": summarize_sessions(
                [s for s in sessions if str(s["sample_id"]) in development_ids]
            ),
            "validation": summarize_sessions(
                [s for s in sessions if str(s["sample_id"]) in validation_ids]
            ),
            "difficulty": {
                bucket: summarize_sessions(
                    [s for s in sessions if difficulty[str(s["sample_id"])] == bucket]
                )
                for bucket in buckets
            },
        }

    return {"seed": seed, "validation_size": validation_size, "weights": results}


def run_popularity_variants(
    variants: dict[str, Path],
    samples: list[dict],
    weights: tuple[float, ...] = DEFAULT_WEIGHTS,
    validation_size: int = 80,
    seed: str = DEFAULT_SEED,
) -> dict:
    results = {
        name: run_popularity_sweep(path, samples, weights, validation_size, seed)
        for name, path in variants.items()
    }
    if set(results) != {"official", "coverage_stress"}:
        return next(iter(results.values()))

    official = results["official"]["weights"]
    stress = results["coverage_stress"]["weights"]
    deltas = {}
    for key in results["official"]["weights"]:
        official_row = official[key]
        stress_row = stress[key]
        deltas[key] = {
            "full": summary_delta(official_row["full"], stress_row["full"]),
            "development": summary_delta(
                official_row["development"], stress_row["development"]
            ),
            "validation": summary_delta(
                official_row["validation"], stress_row["validation"]
            ),
            "difficulty": {
                bucket: summary_delta(
                    official_row["difficulty"][bucket], stress_row["difficulty"][bucket]
                )
                for bucket in sorted(
                    set(official_row["difficulty"]) & set(stress_row["difficulty"])
                )
            },
        }
    return {
        "schema_version": 1,
        "catalogs": results,
        "delta_direction": "coverage_stress_minus_official",
        "deltas": deltas,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tune the popularity prior on the held-out validation split"
    )
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--output", default="reports/experiments/popularity-sweep.json")
    parser.add_argument("--validation-size", type=int, default=80)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--weights", nargs="+", type=float, default=list(DEFAULT_WEIGHTS))
    add_catalog_variant_arguments(parser)
    args = parser.parse_args()

    samples = load_jsonl(args.dataset)
    variants, _manifest = resolve_catalog_variants(
        args.catalog,
        args.dataset,
        args.catalog_mode,
        args.stress_catalog,
        args.stress_manifest,
        seed=args.stress_seed,
    )
    result = run_popularity_variants(
        variants,
        samples,
        weights=tuple(args.weights),
        validation_size=args.validation_size,
        seed=args.seed,
    )
    for weight_key, row in (
        result["weights"].items()
        if "weights" in result
        else result["catalogs"]["official"]["weights"].items()
    ):
        by_difficulty = "  ".join(
            f"{bucket}={row['difficulty'][bucket]['hit_rate_at_10']:.4f}"
            for bucket in row["difficulty"]
        )
        print(f"weight={weight_key:<5} validation={row['validation']['recommended_technical_score']:.6f} "
              f"full={row['full']['recommended_technical_score']:.6f}  {by_difficulty}", flush=True)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
