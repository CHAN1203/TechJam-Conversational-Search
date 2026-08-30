# Buying/Browsing Intent-Aware Routing

Date: 2026-08-29
Status: **current best.** TechnicalScore `0.841838 -> 0.847923`.

## Hypothesis

`TechJam.docx` lists Intent-Aware Routing (Buying vs. Browsing) as a Layer 3
option that has not been implemented: "Dispatches different search
algorithms based on whether the user is picking precisely or casually
browsing." This project's own evidence already points at it directly:
`slot-memory-and-retrieval-ablation.md` measured that every setting which
helped Intent Override (pool 500, catalog IDF) hurt Browsing, and concluded
"this argues for routing rather than a single global setting" -- and named
it as the explicit next step, never executed.

Hypothesis: a Buying customer discloses a concrete constraint on the
opening turn (per `docs/competition_specification.md`: "40% Buying: a hard
constraint is disclosed early"). For those sessions, rewarding candidates
that match **all** currently-known non-durable slot values -- not just
summing per-term field weights, which lets many weak/irrelevant term
matches outscore one candidate that satisfies every real constraint -- should
push the true target higher and faster. A Browsing customer has not
committed to a specific value yet, so applying the same bonus there is not
expected to help (there is nothing solid to require agreement with) and
could over-penalize exploratory diversity.

## Change from the last retained method (E11, TechnicalScore 0.841838)

- New: `_classify_route(first_message, gazetteer)` -- called once, at turn 1
  only, and cached per session (`self._session_route`). Buying if the
  opening message's `extract_slots()` result contains at least one
  non-durable slot (material/color/style/size); Browsing otherwise. This
  mirrors the scenario's own generative definition instead of inventing a
  new heuristic, and never touches turn >= 2 messages or `ground_truth`.
- New: `starter/reranker.py` gains an optional `required_terms` /
  `completeness_bonus` pair. When both are given, a candidate that contains
  every term in `required_terms` (anywhere in the weighted fields) receives
  an additive bonus on top of the existing field-weighted + popularity
  score.
- `starter/agent.py` passes `required_terms=<current non-durable slot terms>`
  and `completeness_bonus=4.0` (one title-weight unit; see Weight Selection)
  to `rerank_candidates` only when the session's cached route is `buying`.
  Browsing sessions call `rerank_candidates` exactly as E11 does -- no
  parameters added, zero behavior change on that path by construction.
- Nothing else changes: retrieval query construction, the popularity prior,
  the override mechanism, and the clarification policy are all untouched.

## Baseline

E11 Popularity Prior, `TechnicalScore 0.841838`, `HitRate@10 0.965`, full
200-session public set, catalog hard-linked from the stable worktree.

## Keep/reject threshold

Keep if full-set `TechnicalScore` improves over `0.841838` with no scenario
regressing by more than 1 session (matching the standard this project has
applied to its own kept-with-caveats results, e.g. E5). Reject if it
regresses TechnicalScore or costs more than 1 session in any scenario.

## Tests that will prove the behavior

1. `_classify_route` returns `buying` when the opening message contains a
   non-durable slot term, `browsing` when it does not.
2. The classification is frozen at turn 1: a later message that adds a slot
   does not change an already-`browsing`-classified session's route.
3. `rerank_candidates` with `required_terms` set gives a strictly higher
   score to a candidate containing every required term than to one missing
   any of them, holding field matches otherwise equal.
4. `rerank_candidates` called without `required_terms` (the existing E11
   call shape) is byte-for-byte unaffected -- a regression guard.
5. An agent-level test: a Buying-classified session's ranking prefers the
   candidate matching every known constraint over a candidate that matches
   more *individual* terms but not all of them together.

## Known risks

- Misclassification: a Browsing session that happens to mention a color
  word in its vague opening message ("something nice, maybe in blue") would
  be routed Buying and get the completeness bonus prematurely. This is a
  structural risk of any turn-1 heuristic and is why the bonus is additive
  (never excludes candidates) rather than a hard filter.
- The bonus weight is a single reasoned value (one title-weight unit, `4.0`),
  not swept. If the result is promising but marginal, a sweep on the
  existing `techjam-clarification-v1` validation split is the natural next
  step before declaring a final value, following the same discipline as
  `popularity-prior.md`.

## Implementation

`starter/agent.py`:

```python
def _classify_route(message_slots: dict[str, list[str]]) -> str:
    if any(slot not in DURABLE_SLOTS for slot in message_slots):
        return "buying"
    return "browsing"
```

Called once per session, at turn 1 only, reusing the `message_slots` already
computed that turn (`extract_slots()` is not called twice). Cached in
`self._session_route[session_id]` and never recomputed for that session.

When the cached route is `"buying"`, `respond()` computes
`required_terms` by tokenizing every currently-known **non-durable** slot
value (material/color/style/size; category/department excluded, matching
the existing override exemption) and intersecting with this turn's actual
query terms, then passes `required_terms` and `completeness_bonus=4.0` to
`rerank_candidates`. Browsing sessions call `rerank_candidates` with an
empty `required_terms` set, which is a no-op by construction (see
`starter/reranker.py`'s `required = set(required_terms or ())`).

`starter/reranker.py`: `rerank_candidates` gains `required_terms` and
`completeness_bonus`. A candidate whose per-term field weights are already
being computed for scoring gets an additive bonus if every required term's
weight is `> 0` (i.e. matched somewhere) -- no second text scan.

10 new tests: 4 in `tests/test_reranker.py` (`CompletenessBonusTest`, plus
the pre-existing suite unaffected), 6 in `tests/test_conversation_state.py`
(`BuyingBrowsingRoutingTest`) covering classification, freezing at turn 1,
and an end-to-end ranking-flip test. All red-green verified individually.
79/79 project tests pass.

## Result

| Metric | E11 (baseline) | E13 (this experiment) | Δ |
| --- | ---: | ---: | ---: |
| HitRate@10 | 0.965 | **0.970** | +0.005 |
| MRR | 0.662125 | **0.671744** | +0.009619 |
| MTTC | 2.965 | **2.930** | -0.035 |
| Efficiency | 0.8035 | **0.8070** | +0.0035 |
| TechnicalScore | 0.841838 | **0.847923** | **+0.006085** |

| Scenario | E11 | E13 |
| --- | ---: | ---: |
| Buying | 0.9500 | **0.9625** (+1 session; MRR 0.696905 -> 0.720952) |
| Browsing | 1.0000 | 1.0000 (unchanged) |
| Intent Override | 0.933333 | 0.933333 (unchanged) |
| Boundary | 0.9000 | 0.9000 (unchanged) |

Every gain is concentrated in Buying, exactly where the hypothesis predicted
it: Browsing, Intent Override, and Boundary are identical to E11 down to the
last digit, because those sessions are classified `"browsing"` and the bonus
is a no-op on that path by construction -- this isn't a coincidence, it's
the intended isolation. Buying improves on *both* HitRate@10 (one more
session found) and MRR (items that were already found now rank higher,
since the bonus reorders within an already-successful retrieval), matching
the "the retrieval was correct, the ranking had no way to prefer the
complete match" framing this experiment set out to test.

## Decision

**Keep. New current best.** Clears the pre-registered threshold (improves
TechnicalScore, no scenario regresses at all, let alone by more than one
session). Reasoning for why it worked, beyond the numbers: `E1`'s
field-weighted reranker already rewards matching *more* terms, but treats
every term independently -- a candidate that racks up several cheap,
tangential matches in low-weight fields can still outscore one that
satisfies every constraint a Buying customer actually stated. Gating a
completeness bonus behind a cheap, structurally-motivated route classifier
(no ground truth, no new dependency, reuses slot memory the override logic
already maintains) captures exactly the gap the doc's Layer 3 routing
concept describes, without touching the three scenarios where it has
nothing useful to add.

## Reproduction

```
python -m unittest discover -s tests -v      # 79 tests
python -m evaluator.local_evaluator          # TechnicalScore 0.847923
```
