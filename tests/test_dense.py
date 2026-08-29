from __future__ import annotations

import unittest

from starter.dense import DenseIndex


PARENT_ASINS = ["SHOE", "JACKET", "BELT", "HAT"]
TEXTS = [
    "Running shoe athletic sneaker footwear jogging trainer",
    "Winter jacket coat outerwear insulated warm",
    "Leather belt buckle accessory waistband",
    "Wide brim hat sun protection headwear",
]


class DenseIndexTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = DenseIndex(PARENT_ASINS, TEXTS, n_components=2)

    def test_finds_the_closest_matching_document(self) -> None:
        results = self.index.search("jogging trainer shoe", top_k=1)
        self.assertEqual(["SHOE"], results)

    def test_empty_query_returns_no_results(self) -> None:
        self.assertEqual(self.index.search("", top_k=4), [])

    def test_search_is_deterministic(self) -> None:
        first = self.index.search("warm winter coat", top_k=4)
        second = self.index.search("warm winter coat", top_k=4)
        self.assertEqual(first, second)

    def test_query_with_zero_vocabulary_overlap_returns_no_results(self) -> None:
        # None of these words appear anywhere in the fitted vocabulary, so
        # there is nothing meaningful to rank against -- empty is the
        # correct, safe answer, not a bug to paper over.
        results = self.index.search("zzz qqq xyzzy plugh", top_k=2)
        self.assertEqual([], results)

    def test_partially_matching_query_still_returns_results(self) -> None:
        results = self.index.search("shoe zzz qqq", top_k=2)
        self.assertEqual(2, len(results))

    def test_respects_top_k(self) -> None:
        results = self.index.search("shoe jacket belt hat", top_k=2)
        self.assertEqual(2, len(results))


if __name__ == "__main__":
    unittest.main()
