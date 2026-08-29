from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping


_PARENTHETICAL_RE = re.compile(r"\([^)]*\)")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

# Canonical departments align with the `categories` vocabulary that customer
# messages echo (Women/Men/Girls/Boys), so baby-* collapses into the matching
# child department rather than forming its own slot value.
_DEPARTMENT_ALIASES = {
    "women": (
        "womens", "women", "ladies", "lady", "female", "adult female",
    ),
    "men": (
        "mens", "men", "male", "adult male", "gentlemen",
    ),
    "girls": (
        "girls", "girl", "baby girls", "teen girls", "toddler girls",
        "little girls", "big girls", "juniors",
    ),
    "boys": (
        "boys", "boy", "baby boys", "teen boys", "toddler boys",
        "little boys", "big boys",
    ),
    "unisex-adult": (
        "unisex adult", "unisex adults", "unisex", "adult unisex", "adult",
    ),
    "unisex-child": (
        "unisex child", "unisex children", "unisex kids", "unisex baby",
        "kids", "kid", "children", "child", "baby", "toddler", "infant",
    ),
}
_DEPARTMENT_LOOKUP = {
    alias: canonical
    for canonical, aliases in _DEPARTMENT_ALIASES.items()
    for alias in aliases
}


def _normalize_key(raw: object) -> str:
    if raw is None:
        return ""
    text = str(raw).lower().replace("'", "").replace("’", "")
    text = _PARENTHETICAL_RE.sub(" ", text)
    return _NON_ALNUM_RE.sub(" ", text).strip()


def normalize_department(raw: object) -> str | None:
    return _DEPARTMENT_LOOKUP.get(_normalize_key(raw))


_TERM_KEEP_RE = re.compile(r"[^a-z0-9&]+")
_COMPOUND_SPLIT_RE = re.compile(r"\s*[&,/]\s*|\s+and\s+", re.IGNORECASE)

# Index 0 of a category path is the frozen catalog root and index 1 is the
# department / merchandising level. Amazon promo nodes ("Prime Day: 30% off",
# "Westlake", "Clearance") only ever appear as a sole child of the root, so
# requiring index >= 2 drops them structurally without a tuned threshold.
_CATEGORY_MIN_DEPTH = 2


# Plurals whose singular keeps the trailing vowel, so the default -ies/-ves/-ses
# rules below would over-strip them. Membership was measured against catalog
# title frequency (e.g. "hoodie" 279 vs "hoody" 17, "blouse" 357 vs "blous" 1);
# the unlisted forms in each class take the default rule (accessories ->
# accessory, scarves -> scarf, dresses -> dress, lenses -> lens).
_SIMPLE_PLURALS = frozenset({
    "hoodies", "neckties", "booties", "beanies", "footies", "skullies",
    "gloves", "sleeves", "adhesives",
    "blouses", "cases", "suitcases", "briefcases", "purses", "chemises",
})


def _singularize(word: str) -> str:
    if len(word) <= 3:
        return word
    if word in _SIMPLE_PLURALS:
        return word[:-1]
    if word.endswith("ves"):
        return word[:-3] + "f"
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith(("ses", "xes", "zes", "ches", "shes")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def normalize_term(raw: object) -> str:
    if raw is None:
        return ""
    text = str(raw).lower().replace("'", "").replace("’", "")
    text = _TERM_KEEP_RE.sub(" ", text)
    return " ".join(_singularize(token) for token in text.split())


def split_compound(raw: object) -> list[str]:
    """Split a compound taxonomy node into separately matchable terms.

    "Tops, Tees & Blouses" lists three product types, so keeping it as one key
    would stop a customer who says "blouse" from matching it.
    """
    parts = _COMPOUND_SPLIT_RE.split(str(raw or ""))
    return [term for part in parts if (term := normalize_term(part))]


def build_category_gazetteer(products: Iterable[dict]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for product in products:
        path = product.get("categories") or []
        terms = {
            term
            for node in path[_CATEGORY_MIN_DEPTH:]
            for term in split_compound(node)
        }
        counts.update(terms)
    return dict(counts)


def build_attribute_seeds(products: Iterable[dict], detail_key: str) -> dict[str, int]:
    """Mine a seed vocabulary for one attribute from a sparse `details` key.

    The structured keys cover only ~5% of the catalog, but across that slice
    they expose the catalog's own surface forms. The vocabulary is what matters
    here; coverage is recovered separately by matching these terms against the
    free text of every product.
    """
    counts: Counter[str] = Counter()
    for product in products:
        details = product.get("details")
        if not isinstance(details, dict) or detail_key not in details:
            continue
        counts.update(set(split_compound(details[detail_key])))
    return dict(counts)


def searchable_terms(product: dict) -> str:
    """Normalized, space-padded title + features text for whole-word matching."""
    features = product.get("features") or []
    if isinstance(features, (list, tuple)):
        feature_text = " ".join(str(item) for item in features)
    else:
        feature_text = str(features)
    normalized = normalize_term(f"{product.get('title') or ''} {feature_text}")
    return f" {normalized} "


def measure_term_coverage(products: Iterable[dict], terms: Iterable[str]) -> dict[str, int]:
    wanted = [term for term in terms]
    counts: Counter[str] = Counter({term: 0 for term in wanted})
    for product in products:
        haystack = searchable_terms(product)
        for term in wanted:
            if f" {term} " in haystack:
                counts[term] += 1
    return dict(counts)


# Attribute slots are seeded from these sparse `details` keys, then given real
# coverage by matching the mined vocabulary against title + features free text.
_ATTRIBUTE_DETAIL_KEYS = {
    "material": "Material",
    "color": "Color",
    "style": "Style",
    "size": "Size",
}


def build_gazetteer(products: Iterable[dict], top_n: int = 60) -> dict[str, dict[str, int]]:
    """Assemble every slot vocabulary from the frozen catalog.

    Attribute slots are keyed by free-text support rather than by the seed
    count, because support is what a customer message can actually match. Terms
    with no free-text support are dropped as catalog noise.
    """
    rows = list(products)
    departments: Counter[str] = Counter()
    for product in rows:
        details = product.get("details")
        if not isinstance(details, dict):
            continue
        if (canonical := normalize_department(details.get("Department"))) is not None:
            departments[canonical] += 1

    gazetteer: dict[str, dict[str, int]] = {
        "department": dict(departments),
        "category": build_category_gazetteer(rows),
    }
    for slot, detail_key in _ATTRIBUTE_DETAIL_KEYS.items():
        seeds = build_attribute_seeds(rows, detail_key)
        ranked = [term for term, _ in sorted(seeds.items(), key=lambda item: -item[1])[:top_n]]
        coverage = measure_term_coverage(rows, ranked)
        gazetteer[slot] = {
            term: count
            for term, count in coverage.items()
            if count > 0 and is_usable_term(term)
        }
    return resolve_slot_conflicts(gazetteer)


def is_usable_term(term: str) -> bool:
    """Reject terms that cannot discriminate between catalog items.

    Bare digits and single letters ("5", "a") match incidentally inside almost
    any title, so a term must carry at least one alphabetic word of length two
    or more to earn a place in a slot vocabulary.
    """
    return any(len(token) >= 2 and token.isalpha() for token in str(term).split())


# Precedence for a term claimed by more than one slot, strongest evidence
# first. Support counts cannot break these ties: category counts come from the
# taxonomy while attribute counts come from free text, and a term like "silver"
# scores identically under material and color because coverage is measured over
# the same text. So the order encodes how trustworthy each source is.
#   department  dedicated structured field behind a curated normalizer
#   material    explicit details.Material values; what the item is made of
#   size        explicit details.Size values
#   category    taxonomy product type; beats Amazon's catch-all Style field
#   color       weak, and the field is full of compound values
#   style       weakest; details.Style collects product types such as "hoodie"
_SLOT_PRECEDENCE = ("department", "material", "size", "category", "color", "style")


def resolve_slot_conflicts(
    gazetteer: Mapping[str, Mapping[str, int]],
) -> dict[str, dict[str, int]]:
    """Give every term exactly one slot.

    A term in two slots corrupts per-slot reasoning: "small" filed under color
    makes a size answer look like a color answer, and an override that names a
    size would then discard the customer's color constraint.
    """
    ranked = [slot for slot in _SLOT_PRECEDENCE if slot in gazetteer]
    ranked += [slot for slot in gazetteer if slot not in _SLOT_PRECEDENCE]
    claimed: set[str] = set()
    resolved: dict[str, dict[str, int]] = {}
    for slot in ranked:
        kept = {
            term: count
            for term, count in gazetteer[slot].items()
            if term not in claimed
        }
        claimed.update(kept)
        resolved[slot] = kept
    return {slot: resolved[slot] for slot in gazetteer}
