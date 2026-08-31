"""Query-side stress diagnostic: how much does the agent depend on the
simulator's exact wording?

T25 stresses the *catalog* by masking sparse fields. Nothing stressed the
*customer*. `docs/competition_specification.md` reserves the organizer's right
to paraphrase simulator output, and E32 weights the category path highest
precisely because the simulator quotes it verbatim, so the exposure is worth
measuring rather than assuming.

Ground truth, the evaluator and the agent are all untouched. Only the message
the agent receives is rewritten, simulating a simulator that words things
differently. The levels are ordered by how much of the customer's information
survives, not by how different the string looks.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping


# The public simulator's fixed sentence frames. Removing these changes the
# phrasing while leaving every constraint the customer disclosed intact.
SCAFFOLD_PHRASES = (
    "A key requirement is:",
    "For that, what matters is:",
    ", but I'm still exploring",
    "Actually, ignore my earlier preference.",
    "What I need is:",
    "please use your judgment.",
    "Those options are not quite right yet. Ask me about one specific attribute.",
)

# Head nouns a customer might reasonably use instead of the catalog's own
# taxonomy word. Chosen to break exact token match rather than to be elegant.
SYNONYMS = {
    "shoes": "footwear", "shoe": "footwear", "shirt": "top", "shirts": "tops",
    "jacket": "coat", "jackets": "coats", "bag": "purse", "bags": "purses",
    "watches": "timepieces", "watch": "timepiece", "sunglasses": "eyewear",
    "necklaces": "chains", "pendants": "charms", "bracelets": "wristbands",
    "sandals": "open footwear", "boots": "high footwear", "socks": "hosiery",
    "wallets": "billfolds", "earrings": "studs", "rings": "bands",
    "sneakers": "trainers", "pants": "trousers", "dress": "gown",
    "hat": "cap", "scarf": "wrap", "gloves": "mittens", "belt": "strap",
}

_OPENING_RE = re.compile(r"(I'm looking for )[^.,]+")
_WORD_RE = re.compile(r"[A-Za-z]+")


def strip_scaffold(message: str) -> str:
    """Remove the simulator's fixed sentence frames, keeping every constraint.

    Args:
        message: One customer utterance.

    Returns:
        The same content in different words. Tests phrasing sensitivity alone.
    """
    out = message
    for phrase in SCAFFOLD_PHRASES:
        out = out.replace(phrase, " ")
    return re.sub(r"\s+", " ", out).strip()


def drop_category(message: str) -> str:
    """Replace the quoted catalog taxonomy with a contentless placeholder.

    `initial_message` builds the opening line from
    `coarse_category(target.categories)`, so this simulates a customer who
    names no taxonomy at all: "I'm looking for Wrist Watches" becomes
    "I'm looking for something". This is the severe level -- it removes
    information rather than rewording it.

    Args:
        message: One customer utterance.

    Returns:
        The message with its opening category phrase replaced.
    """
    return _OPENING_RE.sub(r"\1something", message, count=1)


def substitute_synonyms(message: str) -> str:
    """Swap head nouns for plausible customer-chosen alternatives.

    Rewords without removing information, so a retriever that understands
    meaning rather than surface form should be unaffected.

    Args:
        message: One customer utterance.

    Returns:
        The message with known head nouns replaced.
    """
    return _WORD_RE.sub(
        lambda match: SYNONYMS.get(match.group(0).lower(), match.group(0)), message
    )


STRESS_LEVELS: Mapping[str, Callable[[str], str]] = {
    "L0_clean": lambda message: message,
    "L1_no_scaffold": strip_scaffold,
    "L2_no_category": lambda message: drop_category(strip_scaffold(message)),
    "L3_synonyms_only": substitute_synonyms,
}


class StressAgent:
    """Transparent proxy that rewrites the customer's wording in flight.

    The evaluator drives this exactly as it drives the real agent, so the
    turn loop, the scoring and the ground truth are untouched -- only the
    string the agent reads differs.
    """

    def __init__(self, agent: object, transform: Callable[[str], str]) -> None:
        self.agent = agent
        self.transform = transform

    def reset(self, session_id: str, user_profile: dict) -> None:
        self.agent.reset(session_id, user_profile)

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        return self.agent.respond(
            session_id, self.transform(user_message), turn, top_k
        )
