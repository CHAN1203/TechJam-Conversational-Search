from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence, Set


PROFILE_ATTRIBUTE_MAP = {
    "material": "material",
    "fit": "size",
    "comfort": "feature",
    "durability": "feature",
    "style": "style",
    "weather": "use_case",
    "warmth": "use_case",
    "color": "color",
}
DEFAULT_ATTRIBUTE_ORDER = (
    "material", "size", "style", "feature", "use_case", "color", "brand", "budget", "other",
)
CANDIDATE_PATTERNS = {
    "material": (
        "cotton", "polyester", "nylon", "leather", "wool", "spandex", "silk", "rayon", "fabric",
    ),
    "color": (
        "black", "white", "blue", "red", "pink", "green", "brown", "gray", "grey", "purple",
        "yellow", "orange",
    ),
    "size": ("xs", "small", "medium", "large", "xl", "xxl", "wide", "narrow"),
    "style": (
        "casual", "formal", "classic", "modern", "vintage", "slim", "relaxed", "sleeve", "neck",
    ),
    "use_case": ("hiking", "running", "gym", "winter", "outdoor", "work", "travel", "sport"),
    "feature": (
        "waterproof", "lightweight", "breathable", "pocket", "stretch", "support", "durable",
        "comfortable", "washable",
    ),
}
CANDIDATE_ATTRIBUTE_ORDER = ("material", "color", "size", "style", "use_case", "feature")
TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _profile_order(user_profile: Mapping[str, object]) -> list[str]:
    tags = user_profile.get("preference_tags") or []
    preferred = [
        PROFILE_ATTRIBUTE_MAP[str(tag).lower()]
        for tag in tags
        if str(tag).lower() in PROFILE_ATTRIBUTE_MAP
    ]
    return list(dict.fromkeys([*preferred, *DEFAULT_ATTRIBUTE_ORDER]))


def _candidate_text(candidate: Mapping[str, object]) -> str:
    return " ".join(str(value) for value in candidate.values()).lower()


def _distinct_spread(value_counts: Mapping[str, int]) -> float:
    # Counts distinct values only. Two values split 99/1 score the same as 50/50.
    return (len(value_counts) - 1) / len(value_counts)


def _entropy_spread(value_counts: Mapping[str, int]) -> float:
    # Normalized Shannon entropy over how the values are actually distributed,
    # so an attribute that splits the pool evenly outranks one dominated by a
    # single value. Divided by log2(k) to keep it comparable across attributes
    # with different numbers of observed values.
    total = sum(value_counts.values())
    probabilities = [count / total for count in value_counts.values()]
    entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)
    return entropy / math.log2(len(value_counts))


def _grounded_order(candidates: Sequence[Mapping[str, object]], spread) -> list[str]:
    if not candidates:
        return list(DEFAULT_ATTRIBUTE_ORDER)
    candidate_tokens = [set(TOKEN_RE.findall(_candidate_text(candidate))) for candidate in candidates]
    scores: list[tuple[float, int, str]] = []
    for priority, attribute in enumerate(CANDIDATE_ATTRIBUTE_ORDER):
        pattern_values = set(CANDIDATE_PATTERNS[attribute])
        value_counts: Counter[str] = Counter()
        covered = 0
        for tokens in candidate_tokens:
            matches = tokens & pattern_values
            if matches:
                covered += 1
                value_counts.update(matches)
        if len(value_counts) < 2:
            continue
        coverage = covered / len(candidates)
        scores.append((coverage * spread(value_counts), priority, attribute))
    scores.sort(key=lambda item: (-item[0], item[1]))
    grounded = [attribute for _, _, attribute in scores]
    return list(dict.fromkeys([*grounded, *DEFAULT_ATTRIBUTE_ORDER]))


def _candidate_order(candidates: Sequence[Mapping[str, object]]) -> list[str]:
    return _grounded_order(candidates, _distinct_spread)


def _entropy_order(candidates: Sequence[Mapping[str, object]]) -> list[str]:
    return _grounded_order(candidates, _entropy_spread)


def select_attribute(
    policy: str,
    user_profile: Mapping[str, object],
    asked_attributes: Set[str],
    candidates: Sequence[Mapping[str, object]],
) -> str | None:
    if policy == "other":
        # Diagnostic probe. The local simulator answers "other" with up to two
        # undisclosed constraints while every specific attribute yields one, so
        # repeating it measures the ceiling of what clarification can buy. It is
        # deliberately not a submission strategy: the private simulator policy
        # is not guaranteed to treat "other" the same way.
        return "other"
    if policy == "fixed":
        order = DEFAULT_ATTRIBUTE_ORDER
    elif policy == "profile":
        order = _profile_order(user_profile)
    elif policy == "candidate":
        order = _candidate_order(candidates)
    elif policy == "entropy":
        order = _entropy_order(candidates)
    else:
        raise ValueError(f"unsupported clarification policy: {policy}")
    return next((attribute for attribute in order if attribute not in asked_attributes), None)
