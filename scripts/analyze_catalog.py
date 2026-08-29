from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis.catalog_profile import profile_catalog
from evaluator.local_evaluator import load_jsonl


DEFAULT_FIELDS = (
    "title",
    "features",
    "description",
    "price",
    "categories",
    "details",
    "average_rating",
    "rating_number",
    "store",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument(
        "--output",
        default="reports/baseline/catalog-profile.json",
    )
    parser.add_argument("--field", action="append", dest="fields")
    args = parser.parse_args()
    report = profile_catalog(
        load_jsonl(args.catalog),
        tuple(args.fields or DEFAULT_FIELDS),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
