from __future__ import annotations

import re
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


def _candidate_order(candidates: Sequence[Mapping[str, object]]) -> list[str]:
    if not candidates:
        return list(DEFAULT_ATTRIBUTE_ORDER)
    candidate_tokens = [set(TOKEN_RE.findall(_candidate_text(candidate))) for candidate in candidates]
    scores: list[tuple[float, int, str]] = []
    for priority, attribute in enumerate(CANDIDATE_ATTRIBUTE_ORDER):
        pattern_values = set(CANDIDATE_PATTERNS[attribute])
        observed: set[str] = set()
        covered = 0
        for tokens in candidate_tokens:
            matches = tokens & pattern_values
            if matches:
                covered += 1
                observed.update(matches)
        if len(observed) < 2:
            continue
        coverage = covered / len(candidates)
        diversity = (len(observed) - 1) / len(observed)
        scores.append((coverage * diversity, priority, attribute))
    scores.sort(key=lambda item: (-item[0], item[1]))
    grounded = [attribute for _, _, attribute in scores]
    return list(dict.fromkeys([*grounded, *DEFAULT_ATTRIBUTE_ORDER]))


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
    else:
        raise ValueError(f"unsupported clarification policy: {policy}")
    return next((attribute for attribute in order if attribute not in asked_attributes), None)
