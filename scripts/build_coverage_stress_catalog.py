from __future__ import annotations

import argparse

from analysis.coverage_stress import DEFAULT_SEED, build_coverage_stress_catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument(
        "--output", default="data/generated/catalog-coverage-stress.jsonl"
    )
    parser.add_argument(
        "--manifest", default="reports/experiments/coverage-stress-catalog.json"
    )
    parser.add_argument("--seed", default=DEFAULT_SEED)
    args = parser.parse_args()

    manifest = build_coverage_stress_catalog(
        args.catalog, args.dataset, args.output, args.manifest, seed=args.seed
    )
    print("field\toriginal\tdesired\tmasked\tstress\tshortfall")
    for field, row in manifest["fields"].items():
        print(
            f"{field}\t{row['original_target_present']}\t"
            f"{row['desired_target_present']}\t{row['masked_count']}\t"
            f"{row['stress_target_present']}\t{row['unfillable_shortfall']}"
        )


if __name__ == "__main__":
    main()
