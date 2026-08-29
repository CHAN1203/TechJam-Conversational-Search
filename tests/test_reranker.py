from __future__ import annotations

import unittest

from starter.reranker import rerank_candidates, extract_bigrams


class RerankerTest(unittest.TestCase):
    def test_complete_constraint_match_outranks_earlier_partial_match(self) -> None:
        candidates = [
            {
                "parent_asin": "PARTIAL",
                "title": "Men's Casual Shoes",
                "categories": "Men Shoes",
                "features": "Lightweight everyday footwear",
                "details": "",
                "store": "Example",
                "description": "",
            },
            {
                "parent_asin": "COMPLETE",
                "title": "Trail Boots",
                "categories": "Men Hiking Boots",
                "features": "Full grain leather for hiking",
                "details": "",
                "store": "Example",
                "description": "",
            },
        ]

        ranked = rerank_candidates(
            ["men", "leather", "hiking", "boots"],
            candidates,
            top_k=2,
        )

        self.assertEqual(["COMPLETE", "PARTIAL"], ranked)

    def test_equal_scores_preserve_bm25_order(self) -> None:
        candidates = [
            {
                "parent_asin": "FIRST",
                "title": "Blue Shirt",
                "categories": "Shirts",
                "features": "Cotton",
                "details": "",
                "store": "Example",
                "description": "",
            },
            {
                "parent_asin": "SECOND",
                "title": "Blue Shirt",
                "categories": "Shirts",
                "features": "Cotton",
                "details": "",
                "store": "Example",
                "description": "",
            },
        ]

        ranked = rerank_candidates(["blue", "shirt"], candidates, top_k=2)

        self.assertEqual(["FIRST", "SECOND"], ranked)

if __name__ == "__main__":
    unittest.main()


class CatalogIdfWeightingTest(unittest.TestCase):
    def test_rare_catalog_terms_outweigh_common_ones(self) -> None:
        # Both candidates match exactly one query term in their title, so
        # unweighted field scoring ties them and insertion order wins. A term
        # held by 40 of 50,000 catalog items says far more about what the
        # customer wants than one held by 20,000.
        candidates = [
            {"parent_asin": "COMMON", "title": "shirt"},
            {"parent_asin": "RARE", "title": "balaclava"},
        ]
        ranked = rerank_candidates(
            ["shirt", "balaclava"],
            candidates,
            2,
            idf={"shirt": 0.5, "balaclava": 5.0},
        )
        self.assertEqual(ranked, ["RARE", "COMMON"])

    def test_omitting_idf_keeps_unweighted_field_scoring(self) -> None:
        candidates = [
            {"parent_asin": "COMMON", "title": "shirt"},
            {"parent_asin": "RARE", "title": "balaclava"},
        ]
        self.assertEqual(
            rerank_candidates(["shirt", "balaclava"], candidates, 2),
            ["COMMON", "RARE"],
        )

class PopularityPriorTest(unittest.TestCase):
    def test_popular_candidate_wins_when_constraint_matches_tie(self) -> None:
        # Every belt matching "leather buckle" scores identically on fields, so
        # the tie is currently broken by BM25 order. The target of a real
        # purchase record is far more likely to be a heavily reviewed item.
        candidates = [
            {"parent_asin": "OBSCURE", "title": "leather buckle", "rating_number": 18},
            {"parent_asin": "POPULAR", "title": "leather buckle", "rating_number": 6614},
        ]
        self.assertEqual(
            rerank_candidates(["leather", "buckle"], candidates, 2, popularity_weight=0.3),
            ["POPULAR", "OBSCURE"],
        )

    def test_a_stronger_constraint_match_still_beats_mere_popularity(self) -> None:
        candidates = [
            {"parent_asin": "POPULAR-WEAK", "title": "leather", "rating_number": 900000},
            {"parent_asin": "EXACT", "title": "leather buckle", "rating_number": 5},
        ]
        self.assertEqual(
            rerank_candidates(["leather", "buckle"], candidates, 2, popularity_weight=0.3),
            ["EXACT", "POPULAR-WEAK"],
        )

    def test_default_weight_leaves_ranking_unchanged(self) -> None:
        candidates = [
            {"parent_asin": "OBSCURE", "title": "leather buckle", "rating_number": 18},
            {"parent_asin": "POPULAR", "title": "leather buckle", "rating_number": 6614},
        ]
        self.assertEqual(
            rerank_candidates(["leather", "buckle"], candidates, 2),
            ["OBSCURE", "POPULAR"],
        )


class SemanticScoreTest(unittest.TestCase):
    def test_semantic_score_can_flip_a_lexical_tie(self) -> None:
        candidates = [
            {"parent_asin": "LOW_SIM", "title": "leather belt"},
            {"parent_asin": "HIGH_SIM", "title": "leather belt"},
        ]
        ranked = rerank_candidates(
            ["leather", "belt"],
            candidates,
            2,
            semantic_scores={"LOW_SIM": 0.1, "HIGH_SIM": 0.9},
            semantic_weight=1.0,
        )
        self.assertEqual(["HIGH_SIM", "LOW_SIM"], ranked)

    def test_missing_semantic_score_contributes_zero_not_a_crash(self) -> None:
        candidates = [
            {"parent_asin": "SCORED", "title": "leather belt"},
            {"parent_asin": "UNSCORED", "title": "leather belt"},
        ]
        ranked = rerank_candidates(
            ["leather", "belt"],
            candidates,
            2,
            semantic_scores={"SCORED": 0.9},
            semantic_weight=1.0,
        )
        self.assertEqual(["SCORED", "UNSCORED"], ranked)

    def test_default_semantic_weight_leaves_ranking_unchanged(self) -> None:
        candidates = [
            {"parent_asin": "A", "title": "leather belt"},
            {"parent_asin": "B", "title": "leather belt"},
        ]
        ranked = rerank_candidates(
            ["leather", "belt"], candidates, 2, semantic_scores={"B": 0.9}
        )
        self.assertEqual(["A", "B"], ranked)


class CompletenessBonusTest(unittest.TestCase):
    def test_matching_every_required_term_outranks_more_individual_matches(self) -> None:
        # MORE-HITS matches more individual query terms overall (three cheap
        # feature-field words) and out-scores ALL-MATCH without the bonus --
        # but it is missing "black" entirely, one of the three things a
        # Buying customer actually asked for. ALL-MATCH satisfies every
        # required term and should win once completeness is rewarded.
        candidates = [
            {
                "parent_asin": "ALL-MATCH",
                "title": "Black Leather Belt",
                "categories": "", "features": "", "details": "", "store": "",
                "description": "",
            },
            {
                "parent_asin": "MORE-HITS",
                "title": "Leather Belt",
                "categories": "", "features": "everyday casual outdoor", "details": "",
                "store": "", "description": "",
            },
        ]
        query_terms = ["black", "leather", "belt", "everyday", "casual", "outdoor"]

        without_bonus = rerank_candidates(query_terms, candidates, top_k=2)
        self.assertEqual(["MORE-HITS", "ALL-MATCH"], without_bonus)

        with_bonus = rerank_candidates(
            query_terms,
            candidates,
            top_k=2,
            required_terms={"black", "leather", "belt"},
            completeness_bonus=4.0,
        )
        self.assertEqual(["ALL-MATCH", "MORE-HITS"], with_bonus)

    def test_omitting_required_terms_leaves_ranking_unchanged(self) -> None:
        candidates = [
            {"parent_asin": "A", "title": "leather"},
            {"parent_asin": "B", "title": "leather belt"},
        ]
        self.assertEqual(
            rerank_candidates(["leather", "belt"], candidates, 2, completeness_bonus=4.0),
            ["B", "A"],
        )


class ExtractBigramsTest(unittest.TestCase):
    def test_extracts_consecutive_word_pairs(self) -> None:
        self.assertEqual(
            extract_bigrams("Running shoe for men"),
            ["running shoe", "shoe for", "for men"],
        )

    def test_single_word_has_no_bigrams(self) -> None:
        self.assertEqual(extract_bigrams("shoe"), [])

    def test_empty_text_has_no_bigrams(self) -> None:
        self.assertEqual(extract_bigrams(""), [])


class PhraseBonusTest(unittest.TestCase):
    def test_exact_phrase_match_outranks_the_same_words_apart(self) -> None:
        candidates = [
            {"parent_asin": "APART", "title": "Running errands in a dress shoe"},
            {"parent_asin": "PHRASE", "title": "Comfortable running shoe for men"},
        ]
        ranked = rerank_candidates(
            ["running", "shoe"],
            candidates,
            2,
            phrase_terms=["running shoe"],
            phrase_weight=3.0,
        )
        self.assertEqual(["PHRASE", "APART"], ranked)

    def test_omitting_phrase_terms_leaves_ranking_unchanged(self) -> None:
        candidates = [
            {"parent_asin": "A", "title": "running errands dress shoe"},
            {"parent_asin": "B", "title": "running shoe"},
        ]
        without_phrase = rerank_candidates(["running", "shoe"], candidates, 2)
        with_zero_weight = rerank_candidates(
            ["running", "shoe"], candidates, 2, phrase_terms=["running shoe"], phrase_weight=0.0
        )
        self.assertEqual(without_phrase, with_zero_weight)

    def test_single_word_message_contributes_no_phrase_bonus_without_crashing(self) -> None:
        candidates = [{"parent_asin": "A", "title": "shoe"}]
        ranked = rerank_candidates(
            ["shoe"], candidates, 1, phrase_terms=extract_bigrams("shoe"), phrase_weight=3.0
        )
        self.assertEqual(["A"], ranked)
