"""Tests for the E32 category field weight and the E31 n-gram phrase extension.

E32 raised `FIELD_WEIGHTS["categories"]` from 3.0 to 6.0. The mechanism is
structural rather than tuned: `evaluator.local_evaluator.initial_message`
builds the customer's opening line from `coarse_category(target.categories)`,
so the category words in the query are quoted verbatim from the target's own
category path. Title words are only ever incidental. These tests pin that
ordering so a future field-weight edit cannot silently undo it.

`extract_phrases` (E31) generalises `extract_bigrams` to longer runs. It is
retained at its no-op default `max_n=2` because longer runs did not compose
with the category weight -- see reports/experiments/field-weight-sweep.md.
"""

from __future__ import annotations

import unittest

from starter.reranker import (
    FIELD_WEIGHTS,
    extract_bigrams,
    extract_phrases,
    rerank_candidates,
)


def product(parent_asin: str, **fields) -> dict:
    """Build a candidate with every scored field present but empty by default."""
    base = {name: "" for name in FIELD_WEIGHTS}
    base.update({"parent_asin": parent_asin, "rating_number": 0, "has_price": False})
    base.update(fields)
    return base


class CategoryWeightTest(unittest.TestCase):
    """The category path is the field the customer is known to quote."""

    def test_categories_outrank_title(self) -> None:
        """A category-path match must beat a title match on the same term.

        This is the whole of E32. If someone re-tunes `FIELD_WEIGHTS` and drops
        `categories` back below `title`, this fails.
        """
        self.assertGreater(FIELD_WEIGHTS["categories"], FIELD_WEIGHTS["title"])

    def test_a_category_match_outranks_a_title_match(self) -> None:
        ranked = rerank_candidates(
            ["wallets"],
            [
                product("TITLE_ONLY", title="wallets"),
                product("CATEGORY_ONLY", categories="Travel Accessories Wallets"),
            ],
            top_k=2,
        )
        self.assertEqual(["CATEGORY_ONLY", "TITLE_ONLY"], ranked)

    def test_categories_still_lose_to_a_broader_match(self) -> None:
        """The weight is a preference, not an override.

        A candidate matching both query terms in its title (4.0 + 4.0 = 8.0)
        must still beat one matching a single term in categories (6.0), or the
        reranker would have become a category classifier.
        """
        ranked = rerank_candidates(
            ["wallets", "leather"],
            [
                product("CATEGORY_ONLY", categories="Travel Accessories Wallets"),
                product("BROAD", title="leather wallets"),
            ],
            top_k=2,
        )
        self.assertEqual(["BROAD", "CATEGORY_ONLY"], ranked)


class ExtractPhrasesTest(unittest.TestCase):
    """`extract_phrases` must reproduce `extract_bigrams` at its default."""

    def test_default_matches_extract_bigrams(self) -> None:
        text = "a blue cotton running shirt"
        self.assertEqual(extract_bigrams(text), extract_phrases(text, max_n=2))

    def test_longer_runs_are_emitted_short_to_long(self) -> None:
        self.assertEqual(
            ["a b", "b c", "a b c"],
            extract_phrases("a b c", max_n=3),
        )

    def test_a_run_longer_than_the_text_yields_nothing_extra(self) -> None:
        self.assertEqual(["a b"], extract_phrases("a b", max_n=5))

    def test_max_n_below_two_yields_no_phrases(self) -> None:
        self.assertEqual([], extract_phrases("a b c", max_n=1))

    def test_a_longer_matching_run_scores_above_a_shorter_one(self) -> None:
        """Phrase credit scales with run length, so a 3-word span beats a 2-word one."""
        phrases = extract_phrases("blue cotton shirt", max_n=3)
        ranked = rerank_candidates(
            [],
            [
                product("PAIR_ONLY", title="blue cotton garment"),
                product("FULL_RUN", title="blue cotton shirt"),
            ],
            top_k=2,
            phrase_terms=phrases,
            phrase_weight=1.0,
        )
        self.assertEqual(["FULL_RUN", "PAIR_ONLY"], ranked)


if __name__ == "__main__":
    unittest.main()
