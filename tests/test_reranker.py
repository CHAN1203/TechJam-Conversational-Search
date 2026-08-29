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
