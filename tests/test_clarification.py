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


class EntropyPolicyTest(unittest.TestCase):
    def test_entropy_prefers_the_balanced_split_where_distinct_counts_tie(self) -> None:
        # Both attributes cover every candidate and show exactly two values, so
        # the candidate policy's (k - 1) / k spread ties and falls back to its
        # hardcoded priority. Only the distribution separates them: material is
        # 99/1 and buys almost nothing, color is 50/50 and halves the pool.
        candidates = (
            [{"title": "cotton black shirt"}] * 50
            + [{"title": "cotton white shirt"}] * 49
            + [{"title": "wool white shirt"}]
        )

        self.assertEqual("material", select_attribute("candidate", {}, set(), candidates))
        self.assertEqual("color", select_attribute("entropy", {}, set(), candidates))

    def test_entropy_falls_back_to_the_fixed_order_without_candidates(self) -> None:
        self.assertEqual("material", select_attribute("entropy", {}, set(), []))


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
