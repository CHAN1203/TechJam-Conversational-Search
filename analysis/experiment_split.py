from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from math import floor


def stratified_split(
    samples: list[dict],
    validation_size: int,
    seed: str = "techjam-clarification-v1",
) -> tuple[list[dict], list[dict]]:
    if validation_size < 0 or validation_size > len(samples):
        raise ValueError("validation_size must be between zero and the sample count")
    if not samples:
        return [], []

    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, sample in enumerate(samples):
        key = (
            str(sample.get("scenario_type", "")),
            str(sample.get("difficulty_bucket", "")),
        )
        groups[key].append(index)

    quotas = {
        key: validation_size * len(indices) / len(samples)
        for key, indices in groups.items()
    }
    allocations = {key: floor(quota) for key, quota in quotas.items()}
    remaining = validation_size - sum(allocations.values())
    remainder_order = sorted(
        groups,
        key=lambda key: (-(quotas[key] - allocations[key]), key),
    )
    for key in remainder_order[:remaining]:
        allocations[key] += 1

    validation_indices: set[int] = set()
    for key, indices in groups.items():
        ranked = sorted(
            indices,
            key=lambda index: sha256(
                f"{seed}\0{samples[index].get('sample_id', '')}\0{index}".encode()
            ).digest(),
        )
        validation_indices.update(ranked[:allocations[key]])

    development = [
        sample for index, sample in enumerate(samples)
        if index not in validation_indices
    ]
    validation = [
        sample for index, sample in enumerate(samples)
        if index in validation_indices
    ]
    return development, validation
