from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis.gazetteer import build_gazetteer
from evaluator.local_evaluator import load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mine slot vocabularies from the frozen catalog"
    )
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--output", default="data/gazetteer.json")
    parser.add_argument("--report", default="reports/baseline/gazetteer-coverage.json")
    parser.add_argument("--top-n", type=int, default=60)
    args = parser.parse_args()

    products = load_jsonl(args.catalog)
    gazetteer = build_gazetteer(products, top_n=args.top_n)

    summary = {
        "row_count": len(products),
        "top_n": args.top_n,
        "slots": {
            slot: {
                "term_count": len(terms),
                "covered_items": sum(terms.values()),
                "top_terms": sorted(terms.items(), key=lambda item: -item[1])[:15],
            }
            for slot, terms in sorted(gazetteer.items())
        },
    }

    for path, payload in ((args.output, gazetteer), (args.report, summary)):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
