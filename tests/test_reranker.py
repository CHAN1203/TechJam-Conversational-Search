from __future__ import annotations

import unittest

from starter.reranker import rerank_candidates


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

class PricePresencePriorTest(unittest.TestCase):
    def test_priced_candidate_wins_when_everything_else_ties(self) -> None:
        # 89% of public targets carry a price against 21% of the catalog, and
        # the gap holds within popularity bands. A listing with a price is an
        # active listing, and only active listings get purchased.
        candidates = [
            {"parent_asin": "NO-PRICE", "title": "leather belt", "rating_number": 500},
            {"parent_asin": "PRICED", "title": "leather belt", "rating_number": 500,
             "has_price": True},
        ]
        self.assertEqual(
            rerank_candidates(["leather", "belt"], candidates, 2, price_weight=2.0),
            ["PRICED", "NO-PRICE"],
        )

    def test_price_never_outweighs_a_missing_constraint(self) -> None:
        candidates = [
            {"parent_asin": "PRICED-WEAK", "title": "leather", "has_price": True},
            {"parent_asin": "UNPRICED-EXACT", "title": "leather belt buckle"},
        ]
        self.assertEqual(
            rerank_candidates(["leather", "belt", "buckle"], candidates, 2, price_weight=2.0),
            ["UNPRICED-EXACT", "PRICED-WEAK"],
        )

    def test_default_price_weight_changes_nothing(self) -> None:
        candidates = [
            {"parent_asin": "NO-PRICE", "title": "leather belt", "rating_number": 500},
            {"parent_asin": "PRICED", "title": "leather belt", "rating_number": 500,
             "has_price": True},
        ]
        self.assertEqual(
            rerank_candidates(["leather", "belt"], candidates, 2),
            ["NO-PRICE", "PRICED"],
        )

class AverageRatingPriorTest(unittest.TestCase):
    def test_better_rated_candidate_wins_when_everything_else_ties(self) -> None:
        candidates = [
            {"parent_asin": "MEDIOCRE", "title": "leather belt",
             "rating_number": 500, "average_rating": 3.5},
            {"parent_asin": "WELL-RATED", "title": "leather belt",
             "rating_number": 500, "average_rating": 4.8},
        ]
        self.assertEqual(
            rerank_candidates(["leather", "belt"], candidates, 2, rating_weight=2.0),
            ["WELL-RATED", "MEDIOCRE"],
        )

    def test_missing_average_rating_is_treated_as_unrated_not_as_an_error(self) -> None:
        candidates = [
            {"parent_asin": "RATED", "title": "leather belt", "average_rating": 4.5},
            {"parent_asin": "UNRATED", "title": "leather belt"},
        ]
        self.assertEqual(
            rerank_candidates(["leather", "belt"], candidates, 2, rating_weight=2.0),
            ["RATED", "UNRATED"],
        )

    def test_default_rating_weight_changes_nothing(self) -> None:
        candidates = [
            {"parent_asin": "MEDIOCRE", "title": "leather belt", "average_rating": 3.5},
            {"parent_asin": "WELL-RATED", "title": "leather belt", "average_rating": 4.8},
        ]
        self.assertEqual(
            rerank_candidates(["leather", "belt"], candidates, 2),
            ["MEDIOCRE", "WELL-RATED"],
        )
