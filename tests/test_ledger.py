from __future__ import annotations

import unittest
from unittest.mock import patch

import starter.agent

from starter.agent import Agent
from starter.agent import _stated_strength
from starter.ledger import (
    ACTIVE,
    HARD,
    UNKNOWN,
    ANSWERED,
    REVOKED,
    SUPERSEDED,
    VOLUNTEERED,
    ConstraintLedger,
    assign_slots,
)
from tests.test_conversation_state import AgentFixture


DURABLE = ("category", "department")
OPENING = 1


class AssignSlotsTest(unittest.TestCase):
    def test_multi_word_slot_terms_reach_the_customers_own_tokens(self) -> None:
        tokens = ["accessories", "belts", "buckle", "closure"]

        assigned = assign_slots(tokens, {"category": ["belt buckle"]})

        self.assertEqual({"belts": "category", "buckle": "category"}, assigned)

    def test_a_token_belongs_to_the_first_slot_that_claims_it(self) -> None:
        assigned = assign_slots(
            ["leather"], {"material": ["leather"], "style": ["leather"]}
        )

        self.assertIn(assigned["leather"], {"material", "style"})
        self.assertEqual(1, len(assigned))


class LedgerRecordTest(unittest.TestCase):
    def test_unclassified_tokens_become_entries_and_are_projected(self) -> None:
        # Stage 0 measured that dropping these narrows the FTS5 query and costs
        # intent_override sessions, so slot=None entries are first-class.
        ledger = ConstraintLedger()

        ledger.record(["hand", "wash"], {}, 1, VOLUNTEERED)

        self.assertEqual(["hand", "wash"], ledger.project(40))
        self.assertEqual([None, None], [entry.slot for entry in ledger.entries()])

    def test_restating_a_term_refreshes_its_last_turn_without_moving_it(self) -> None:
        ledger = ConstraintLedger()
        ledger.record(["belt", "leather"], {}, 1, VOLUNTEERED)

        ledger.record(["leather"], {}, 4, ANSWERED)

        leather = next(e for e in ledger.entries() if e.surface == "leather")
        self.assertEqual(1, leather.first_turn)
        self.assertEqual(4, leather.last_turn)
        self.assertEqual(["belt", "leather"], ledger.project(40))

    def test_a_later_message_can_classify_a_token_seen_unclassified(self) -> None:
        ledger = ConstraintLedger()
        ledger.record(["leather"], {}, 1, VOLUNTEERED)

        ledger.record(["leather"], {"leather": "material"}, 2, ANSWERED)

        self.assertEqual("material", ledger.entries()[0].slot)

    def test_projection_respects_the_term_limit(self) -> None:
        ledger = ConstraintLedger()
        ledger.record([f"t{index}" for index in range(50)], {}, 1, VOLUNTEERED)

        self.assertEqual(40, len(ledger.project(40)))


class LedgerOverrideTest(unittest.TestCase):
    def _ledger(self) -> ConstraintLedger:
        ledger = ConstraintLedger()
        ledger.record(
            ["belts", "closure", "black"],
            {"belts": "category", "black": "color"},
            1,
            VOLUNTEERED,
        )
        ledger.record(["casual"], {"casual": "style"}, 3, ANSWERED)
        return ledger

    def test_each_rule_sets_the_status_it_owns(self) -> None:
        ledger = self._ledger()

        ledger.apply_override({"color": ["blue"]}, DURABLE, OPENING)

        status = {entry.surface: entry.status for entry in ledger.entries()}
        self.assertEqual(ACTIVE, status["belts"])       # durable slot
        self.assertEqual(SUPERSEDED, status["black"])   # slot named by the message
        self.assertEqual(ACTIVE, status["casual"])      # learned after turn 1
        self.assertEqual(REVOKED, status["closure"])    # volunteered at turn 1

    def test_the_override_keeps_the_customers_own_wording(self) -> None:
        # The gazetteer stores "belt"; the customer said "belts". FTS5 does not
        # stem, so projecting the singular would change what the query matches.
        ledger = self._ledger()

        ledger.apply_override({"color": ["blue"]}, DURABLE, OPENING)

        self.assertIn("belts", ledger.project(40))
        self.assertNotIn("belt", ledger.project(40))

    def test_an_unclassified_answer_survives_the_override(self) -> None:
        # E11 cannot do this: unclassified tokens live only in the term list it
        # discards, so an answer given at turn 2 is lost with the rest.
        ledger = ConstraintLedger()
        ledger.record(["belts"], {"belts": "category"}, 1, VOLUNTEERED)
        ledger.record(["waterproof"], {}, 2, ANSWERED)

        ledger.apply_override({"material": ["leather"]}, DURABLE, OPENING)

        self.assertIn("waterproof", ledger.project(40))

    def test_restating_a_revoked_term_brings_it_back(self) -> None:
        ledger = self._ledger()
        ledger.apply_override({"color": ["blue"]}, DURABLE, OPENING)

        ledger.record(["closure"], {}, 3, ANSWERED)

        self.assertIn("closure", ledger.project(40))

    def test_slots_view_reports_only_active_slotted_entries(self) -> None:
        ledger = self._ledger()

        ledger.apply_override({"color": ["blue"]}, DURABLE, OPENING)

        self.assertEqual(
            {"category": {"belts": 1}, "style": {"casual": 3}}, ledger.slots_view()
        )


class AgentStateModelTest(AgentFixture, unittest.TestCase):
    CATALOG = [
        {
            "parent_asin": "LEATHER-BELT",
            "title": "Leather Belt",
            "categories": ["Accessories", "Belts"],
            "features": ["Buckle closure"],
            "details": {"material": "leather"},
            "store": "Example",
            "description": [],
        },
        {
            "parent_asin": "CANVAS-BELT",
            "title": "Canvas Belt",
            "categories": ["Accessories", "Belts"],
            "features": ["Clip closure"],
            "details": {"material": "canvas"},
            "store": "Example",
            "description": [],
        },
    ]
    GAZETTEER = {"category": {"belt": 2}, "material": {"leather": 1, "canvas": 1}}

    def test_the_defaults_are_the_retained_configuration(self) -> None:
        # The organizer runs Agent(catalog_path) with no arguments, so whatever
        # the constructor defaults to is what gets scored.
        agent = self.build_agent(self.CATALOG)

        self.assertEqual("ledger", agent.state_model)
        self.assertEqual(1, agent.no_gain_probe)

    def test_e11_remains_reproducible_from_explicit_flags(self) -> None:
        agent = self.build_agent(self.CATALOG)
        agent.state_model, agent.no_gain_probe = "slots", None
        agent.reset("session", {})

        response = agent.respond("session", "I want a leather belt", 1, 2)

        self.assertEqual("slots", agent.state_model)
        self.assertTrue(response["recommendations"])

    def test_an_unsupported_state_model_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Agent(state_model="transcript")

    def _run(self, model: str, messages: list[str]) -> list[list[str]]:
        agent = self.build_agent(self.CATALOG, gazetteer=self.GAZETTEER)
        agent.state_model = model
        agent.reset("session", {})
        return [
            [item["parent_asin"] for item in agent.respond("session", message, turn, 2)["recommendations"]]
            for turn, message in enumerate(messages, start=1)
        ]

    def test_without_an_override_the_two_models_agree_exactly(self) -> None:
        # The models differ only in how an override is reconciled, so every
        # buying, browsing and boundary session must be unaffected.
        messages = [
            "I'm looking for a leather belt",
            "For that, what matters is: buckle closure.",
            "I don't have an additional preference for color.",
        ]

        self.assertEqual(self._run("slots", messages), self._run("ledger", messages))

    def test_the_ledger_keeps_wording_the_slot_model_normalizes_away(self) -> None:
        messages = [
            "I'm looking for Accessories Belts",
            "Actually, ignore my earlier preference. What I need is: leather.",
        ]
        agents = {}
        for model in ("slots", "ledger"):
            agent = self.build_agent(self.CATALOG, gazetteer=self.GAZETTEER)
            agent.state_model = model
            agent.reset("session", {})
            for turn, message in enumerate(messages, start=1):
                agent.respond("session", message, turn, 2)
            agents[model] = agent._session_terms["session"]

        self.assertIn("belt", agents["slots"])
        self.assertNotIn("belts", agents["slots"])
        self.assertIn("belts", agents["ledger"])


class InformationGainProbeTest(AgentFixture, unittest.TestCase):
    """Stage 2: the agent notices, from its own state, that asking has stopped
    paying, and switches to an open question."""

    CATALOG = AgentStateModelTest.CATALOG
    GAZETTEER = AgentStateModelTest.GAZETTEER

    def _agent(self, **kwargs) -> Agent:
        agent = self.build_agent(self.CATALOG, gazetteer=self.GAZETTEER)
        for name, value in kwargs.items():
            setattr(agent, name, value)
        agent.reset("session", {})
        return agent

    def test_the_probe_is_on_by_default_at_threshold_one(self) -> None:
        self.assertEqual(1, self.build_agent(self.CATALOG).no_gain_probe)

    def test_a_reply_carrying_no_new_constraint_triggers_an_open_question(self) -> None:
        agent = self._agent(state_model="ledger", no_gain_probe=1)

        first = agent.respond("session", "I'm looking for a leather belt", 1, 2)
        second = agent.respond(
            "session", "I don't have an additional preference for color.", 2, 2
        )

        self.assertNotEqual("other", first["ask_attribute"])
        self.assertEqual("other", second["ask_attribute"])

    def test_new_information_resets_the_probe(self) -> None:
        agent = self._agent(state_model="ledger", no_gain_probe=1)
        agent.respond("session", "I'm looking for a belt", 1, 2)
        agent.respond("session", "I don't have an additional preference for size.", 2, 2)

        third = agent.respond("session", "For that, what matters is: canvas.", 3, 2)

        self.assertNotEqual("other", third["ask_attribute"])

    def test_a_higher_threshold_tolerates_one_empty_reply(self) -> None:
        agent = self._agent(state_model="ledger", no_gain_probe=2)
        agent.respond("session", "I'm looking for a belt", 1, 2)

        second = agent.respond(
            "session", "I don't have an additional preference for color.", 2, 2
        )
        third = agent.respond(
            "session", "I don't have an additional preference for size.", 3, 2
        )

        self.assertNotEqual("other", second["ask_attribute"])
        self.assertEqual("other", third["ask_attribute"])

    def test_the_slot_model_never_fires_the_probe(self) -> None:
        # The signal is a ledger property; the retained E11 path has no
        # equivalent and must be unaffected by the flag.
        agent = self._agent(state_model="slots", no_gain_probe=1)
        agent.respond("session", "I'm looking for a belt", 1, 2)

        second = agent.respond(
            "session", "I don't have an additional preference for color.", 2, 2
        )

        self.assertNotEqual("other", second["ask_attribute"])


class StuckConversationTest(AgentFixture, unittest.TestCase):
    """How the agent behaves once the information-gain probe says it is stuck.

    The implicit-rejection penalty used to live here too. It was retired after
    the merged-system ablation measured its marginal contribution at 0.000083;
    see reports/experiments/merged-system-ablation.md.
    """

    CATALOG = AgentStateModelTest.CATALOG
    GAZETTEER = AgentStateModelTest.GAZETTEER

    def _agent(self, **kwargs) -> Agent:
        agent = self.build_agent(self.CATALOG, gazetteer=self.GAZETTEER)
        for name, value in kwargs.items():
            setattr(agent, name, value)
        agent.reset("session", {})
        return agent

    def test_a_persistently_stuck_agent_never_repeats_a_question(self) -> None:
        """E17 measured the alternative and this is why it was rejected.

        Routing this branch through the clarification policy, with the asked
        set dropped so it may repeat, returns the same attribute every turn:
        which attribute best separates the candidates is stable even as the
        rejection penalty shuffles individual products. Round-robin coverage is
        what keeps a stuck conversation from asking one dead question forever.
        """
        agent = self._agent(state_model="ledger", no_gain_probe=1)
        agent.respond("session", "I want a leather belt", 1, 2)
        asked = [
            agent.respond("session", f"I don't have an additional preference for x{i}.", i + 2, 2)[
                "ask_attribute"
            ]
            for i in range(6)
        ]

        self.assertEqual(len(asked), len(set(asked)))

    def test_a_stuck_agent_keeps_asking_instead_of_repeating_other(self) -> None:
        # "other" being a strict superset of every named attribute is a property
        # of this simulator, not of shoppers. The agent must not conclude from
        # one empty answer that nothing is left.
        agent = self._agent(state_model="ledger", no_gain_probe=1)
        agent.respond("session", "I want a leather belt", 1, 2)
        asked = [
            agent.respond("session", f"I don't have an additional preference for x{i}.", i + 2, 2)[
                "ask_attribute"
            ]
            for i in range(4)
        ]

        self.assertEqual("other", asked[0])
        self.assertNotIn("other", asked[1:])
        self.assertEqual(len(asked[1:]), len(set(asked[1:])))


class ConstraintStrengthTest(unittest.TestCase):
    """Recorded, not scored. See T41: two ways of acting on it were measured
    and rejected, but the signal itself is exact and free to keep."""

    def test_both_evaluator_markers_identify_a_requirement(self) -> None:
        self.assertEqual(HARD, _stated_strength(
            "I'm looking for Belts. A key requirement is: leather."))
        self.assertEqual(HARD, _stated_strength(
            "Actually, ignore my earlier preference. What I need is: leather."))

    def test_an_unmarked_message_stays_unknown(self) -> None:
        # A shopper phrasing a requirement their own way is not detected, which
        # is why nothing downstream may treat UNKNOWN as "soft".
        self.assertEqual(UNKNOWN, _stated_strength("I really must have leather"))
        self.assertEqual(UNKNOWN, _stated_strength(
            "For that, what matters is: Buckle closure."))

    def test_hard_surfaces_reports_only_active_marked_entries(self) -> None:
        ledger = ConstraintLedger()
        ledger.record(["leather"], {"leather": "material"}, 1, VOLUNTEERED, HARD)
        ledger.record(["closure"], {}, 1, VOLUNTEERED)

        self.assertEqual({"leather"}, ledger.hard_surfaces())

    def test_a_revoked_requirement_is_no_longer_hard(self) -> None:
        ledger = ConstraintLedger()
        ledger.record(["closure"], {}, 1, VOLUNTEERED, HARD)

        ledger.apply_override({}, DURABLE, OPENING)

        self.assertEqual(set(), ledger.hard_surfaces())

    def test_restating_upgrades_but_a_later_mention_never_downgrades(self) -> None:
        ledger = ConstraintLedger()
        ledger.record(["leather"], {}, 1, VOLUNTEERED)
        self.assertEqual(set(), ledger.hard_surfaces())

        ledger.record(["leather"], {}, 2, ANSWERED, HARD)
        self.assertEqual({"leather"}, ledger.hard_surfaces())

        ledger.record(["leather"], {}, 3, ANSWERED)
        self.assertEqual({"leather"}, ledger.hard_surfaces())


if __name__ == "__main__":
    unittest.main()
