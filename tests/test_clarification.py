from __future__ import annotations

import unittest

from starter.clarification import select_attribute


class ClarificationPolicyTest(unittest.TestCase):
    def test_fixed_ignores_profile_while_profile_policy_uses_it(self) -> None:
        profile = {"preference_tags": ["style"]}

        fixed = select_attribute("fixed", profile, set(), [])
        guided = select_attribute("profile", profile, set(), [])

        self.assertEqual("material", fixed)
        self.assertEqual("style", guided)

    def test_candidate_policy_asks_about_a_varied_grounded_attribute(self) -> None:
        candidates = [
            {"title": "Red Shirt", "features": "Cotton"},
            {"title": "Blue Shirt", "features": "Cotton"},
            {"title": "Green Shirt", "features": "Cotton"},
        ]

        selected = select_attribute("candidate", {}, set(), candidates)

        self.assertEqual("color", selected)

    def test_balanced_policy_prefers_a_profile_attribute_that_varies(self) -> None:
        candidates = [
            {"title": "Red Casual Shirt", "features": "Cotton"},
            {"title": "Blue Formal Shirt", "features": "Cotton"},
        ]

        try:
            selected = select_attribute(
                "balanced",
                {"preference_tags": ["style"]},
                set(),
                candidates,
            )
        except ValueError:
            selected = None

        self.assertEqual("style", selected)

    def test_balanced_policy_skips_a_profile_attribute_that_does_not_vary(self) -> None:
        candidates = [
            {"title": "Red Shirt", "features": "Cotton"},
            {"title": "Blue Shirt", "features": "Cotton"},
        ]

        try:
            selected = select_attribute(
                "balanced",
                {"preference_tags": ["material"]},
                set(),
                candidates,
            )
        except ValueError:
            selected = None

        self.assertEqual("color", selected)


if __name__ == "__main__":
    unittest.main()
