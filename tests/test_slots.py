from __future__ import annotations

import unittest

from starter.slots import extract_slots


GAZETTEER = {
    "category": {"running shoe": 5, "shoe": 40, "dress": 20},
    "material": {"leather": 10, "faux leather": 3},
    "color": {"black": 8},
    "department": {"men": 30},
}


class ExtractSlotsTest(unittest.TestCase):
    def test_assigns_matched_terms_to_their_slots(self) -> None:
        self.assertEqual(
            extract_slots("I want a black leather dress", GAZETTEER),
            {"category": ["dress"], "material": ["leather"], "color": ["black"]},
        )

    def test_prefers_the_longest_match_and_drops_terms_it_contains(self) -> None:
        self.assertEqual(
            extract_slots("looking for a running shoe", GAZETTEER),
            {"category": ["running shoe"]},
        )

    def test_matches_singular_and_plural_surface_forms(self) -> None:
        self.assertEqual(
            extract_slots("I need mens dresses", GAZETTEER),
            {"category": ["dress"], "department": ["men"]},
        )

    def test_returns_empty_mapping_when_nothing_matches(self) -> None:
        self.assertEqual(extract_slots("hello there", GAZETTEER), {})

    def test_ignores_substring_collisions(self) -> None:
        self.assertEqual(extract_slots("blackberry preserves", GAZETTEER), {})

    def test_recognizes_pu_as_the_faux_leather_material(self) -> None:
        self.assertEqual(
            extract_slots("looking for a PU bag", GAZETTEER),
            {"material": ["faux leather"]},
        )

    def test_pu_leather_resolves_to_faux_leather_not_leather(self) -> None:
        self.assertEqual(
            extract_slots("PU leather wallet", GAZETTEER),
            {"material": ["faux leather"]},
        )

    def test_pleather_resolves_to_faux_leather(self) -> None:
        self.assertEqual(
            extract_slots("a pleather jacket", GAZETTEER),
            {"material": ["faux leather"]},
        )


if __name__ == "__main__":
    unittest.main()
