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


if __name__ == "__main__":
    unittest.main()


class AlwaysOtherPolicyTest(unittest.TestCase):
    def test_always_asks_other_even_when_already_asked(self) -> None:
        # Diagnostic probe only: the local simulator answers "other" with up to
        # two undisclosed constraints while every specific attribute yields one,
        # so repeating it measures the ceiling of what clarification can buy.
        self.assertEqual(select_attribute("other", {}, set(), []), "other")
        self.assertEqual(select_attribute("other", {}, {"other"}, []), "other")
        self.assertEqual(
            select_attribute("other", {"preference_tags": ["material"]}, {"other", "material"}, []),
            "other",
        )
