"""Tests for the query-side stress diagnostic (T43)."""

from __future__ import annotations

import unittest

from analysis.query_stress import (
    STRESS_LEVELS,
    StressAgent,
    drop_category,
    strip_scaffold,
    substitute_synonyms,
)


BUYING = "I'm looking for Watches Wrist Watches. A key requirement is: Imported."
BROWSING = "I'm looking for Bras Sports Bras, but I'm still exploring."


class TransformTest(unittest.TestCase):
    """Each level must change what it claims to change, and nothing else."""

    def test_strip_scaffold_keeps_the_disclosed_constraint(self) -> None:
        out = strip_scaffold(BUYING)
        self.assertNotIn("A key requirement is:", out)
        self.assertIn("Imported", out)
        self.assertIn("Wrist Watches", out)

    def test_drop_category_removes_the_quoted_taxonomy(self) -> None:
        out = drop_category(BUYING)
        self.assertIn("I'm looking for something", out)
        self.assertNotIn("Wrist Watches", out)

    def test_drop_category_leaves_later_sentences_intact(self) -> None:
        """Only the opening category phrase goes; disclosed constraints stay."""
        self.assertIn("Imported", drop_category(BUYING))

    def test_synonyms_replace_known_head_nouns(self) -> None:
        out = substitute_synonyms(BUYING)
        self.assertIn("timepieces", out.lower())
        self.assertNotIn("watches", out.lower())
        # Rewording only: the disclosed constraint and the frame survive.
        self.assertIn("Imported", out)
        self.assertIn("A key requirement is:", out)

    def test_synonyms_leave_unknown_words_alone(self) -> None:
        """A head noun absent from the map is a no-op, not a corruption."""
        self.assertEqual(BROWSING, substitute_synonyms(BROWSING))

    def test_every_level_returns_a_string(self) -> None:
        for name, transform in STRESS_LEVELS.items():
            with self.subTest(level=name):
                self.assertIsInstance(transform(BUYING), str)

    def test_l0_is_the_identity(self) -> None:
        self.assertEqual(BUYING, STRESS_LEVELS["L0_clean"](BUYING))


class StressAgentTest(unittest.TestCase):
    """The proxy must forward everything except the message text."""

    class Recorder:
        def __init__(self) -> None:
            self.seen: list[str] = []
            self.reset_calls: list[str] = []

        def reset(self, session_id: str, user_profile: dict) -> None:
            self.reset_calls.append(session_id)

        def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
            self.seen.append(user_message)
            return {"message": "", "ask_attribute": None, "recommendations": []}

    def test_the_agent_sees_the_transformed_message(self) -> None:
        recorder = self.Recorder()
        agent = StressAgent(recorder, str.upper)
        agent.reset("s", {})
        agent.respond("s", "hello", 1, 10)
        self.assertEqual(["HELLO"], recorder.seen)
        self.assertEqual(["s"], recorder.reset_calls)

    def test_reset_is_not_transformed(self) -> None:
        """Only `respond` carries customer wording; `reset` must pass through."""
        recorder = self.Recorder()
        StressAgent(recorder, str.upper).reset("session-id", {"summary": "x"})
        self.assertEqual(["session-id"], recorder.reset_calls)


if __name__ == "__main__":
    unittest.main()
