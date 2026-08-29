from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis.experiment_results import summarize_sessions
from analysis.experiment_split import stratified_split
from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
from starter.agent import Agent


DEFAULT_WEIGHTS = (0.0, 0.15, 0.3, 0.5, 0.8, 1.2)
DEFAULT_SEED = "techjam-clarification-v1"


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
    args = parser.parse_args()

    samples = load_jsonl(args.dataset)
    development, validation = stratified_split(samples, args.validation_size, args.seed)
    development_ids = {str(s["sample_id"]) for s in development}
    validation_ids = {str(s["sample_id"]) for s in validation}
    catalog_ids, categories, products = catalog_index(args.catalog)

    # A prior this strong could lift only the easy sessions while leaving the
    # hard ones untouched, which would inflate the total without the agent
    # getting better. Reporting by difficulty makes that visible.
    difficulty = {
        str(sample["sample_id"]): str(sample.get("difficulty_bucket", "unknown"))
        for sample in samples
    }
    buckets = sorted(set(difficulty.values()))

    results: dict[str, dict] = {}
    for weight in args.weights:
        sessions = evaluate(
            Agent(args.catalog, popularity_weight=weight),
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
        row = results[f"{weight:g}"]
        by_difficulty = "  ".join(
            f"{bucket}={row['difficulty'][bucket]['hit_rate_at_10']:.4f}"
            for bucket in buckets
        )
        print(f"weight={weight:<5g} validation={row['validation']['recommended_technical_score']:.6f} "
              f"full={row['full']['recommended_technical_score']:.6f}  {by_difficulty}", flush=True)

    payload = {"seed": args.seed, "validation_size": args.validation_size, "weights": results}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
