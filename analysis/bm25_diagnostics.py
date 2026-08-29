from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence


def rank_of(target_id: str, ranked_ids: Sequence[str]) -> int | None:
    try:
        return ranked_ids.index(target_id) + 1
    except ValueError:
        return None


def _recall(ranks: Sequence[int | None], cutoffs: tuple[int, ...]) -> dict[str, float]:
    if not ranks:
        return {str(cutoff): 0.0 for cutoff in cutoffs}
    return {
        str(cutoff): round(
            sum(rank is not None and rank <= cutoff for rank in ranks) / len(ranks),
            6,
        )
        for cutoff in cutoffs
    }


def summarize_ranks(records: Iterable[dict], cutoffs: tuple[int, ...]) -> dict:
    materialized = list(records)
    grouped: dict[str, list[int | None]] = defaultdict(list)
    for record in materialized:
        grouped[str(record["scenario_type"])].append(record.get("rank"))
    return {
        "sample_count": len(materialized),
        "recall": _recall(
            [record.get("rank") for record in materialized],
            cutoffs,
        ),
        "scenario_recall": {
            name: {
                "sample_count": len(ranks),
                "recall": _recall(ranks, cutoffs),
            }
            for name, ranks in sorted(grouped.items())
        },
    }
