  # Experiment History and Method Comparison Matrix

  This file is the project's experiment ledger. Every change to retrieval,
  ranking, conversation state, or question policy must add a result here,
  including failed experiments. It should answer three questions directly:

  1. Where did the project start?
  2. What changed in each experiment?
  3. Which method is best, and why was each method kept or rejected?

> Current best: E13-C Constraint Ledger with the information-gain probe, with
> public HitRate@10 `0.980`, MRR `0.698381`, MTTC `2.540`, and TechnicalScore
> `0.868714`. Recommended configuration:
> `Agent(state_model="ledger", no_gain_probe=1)`. Constructor defaults remain
> `state_model="slots"` and `no_gain_probe=None`, so an unflagged `Agent()`
> still reproduces E11 at `0.841838`.

  Follow the [experiment workflow](EXPERIMENT_WORKFLOW.md) before starting or
  recording another method.

  ## 1. Method comparison matrix

  All formal results use the full 200-session public set, the frozen 50,000-item
  catalog, and the unmodified official evaluator. `Δ` is measured against the
  previous retained method.

| ID | Method | Main change | Automated tests | HitRate@10 | Δ HitRate | MRR | MTTC ↓ | Efficiency | TechnicalScore | Δ Score | Decision | Commit |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| E0 | Weak BM25 baseline | Return BM25 Top-10 directly; no state or questions | 3 | 0.125 | Reference | 0.068034 | 9.810 | 0.1190 | 0.106710 | Reference | Baseline | `3407835` |
| E1 | Field reranker v1 | Rerank BM25 Top-100 by field coverage | 10 | 0.160 | +0.035 | 0.076750 | 9.460 | 0.1540 | 0.133825 | +0.027115 | **Keep** | `db65ad2` |
| E1-A | Reranker + BM25 rank prior | Add the original BM25 rank as a bonus to E1 | Targeted | 0.155 | -0.005 | 0.073992 | 9.510 | 0.1490 | 0.129498 | -0.004327 | Reject | Not committed |
| E2 | Conversation State v1 | Accumulate constraints, handle overrides, ask profile-guided non-repeating questions | 14 | 0.870 | +0.710 | 0.533748 | 4.565 | 0.6435 | 0.723824 | +0.589999 | Keep | `d770b6f` |
| E3-A | Fixed clarification | Use a fixed attribute question order | 21 | 0.865 | -0.005 | 0.523492 | 4.640 | 0.6360 | 0.716748 | -0.007076 | Reject | `fa84de2` |
| E3-B | Profile clarification | Use the E2 profile-first policy as the ablation baseline | 21 | 0.870 | +0.000 | 0.533748 | 4.565 | 0.6435 | 0.723824 | +0.000000 | Previous baseline | `fa84de2` |
| E3-C | Candidate-aware clarification | Ask first about a covered, varied attribute in the Top-100 candidates | 21 | **0.870** | **+0.000** | **0.544236** | **4.410** | **0.6590** | **0.730071** | **+0.006247** | Superseded by E9 | `fa84de2` |
| E4-A | Balanced clarification | Prioritize the intersection of profile preferences and current product differences | 23 during experiment | 0.870 | +0.000 | 0.536248 | 4.540 | 0.6460 | 0.725074 | -0.004997 | Reject | Review branch only |
| E4-B | Always-ask-other probe | Always ask `other`; diagnostic only | 35 | 0.840 | -0.030 | 0.522508 | 3.635 | 0.7365 | 0.724052 | -0.006019 | Reject (diagnostic) | Not separately committed |
| E5 | Slot-aware override memory | Preserve category/department slots during override; clear the rest | 41 | **0.875** | +0.005 | 0.540300 | **4.290** | 0.6710 | **0.733790** | +0.003719 | Keep (weak evidence) | Included in remote series |
| E6 | Turn-aware override memory | Also preserve constraints learned from turn 2 onward | 48 | 0.875 | +0.000 | 0.540300 | 4.290 | 0.6710 | 0.733790 | +0.000000 | Reject (no effect) | Included in remote series |
| E7 | Candidate pool 100 -> 500 | Increase only the BM25 candidate pool | 51 | 0.875 | +0.000 | 0.528762 | 4.190 | 0.6810 | 0.732329 | -0.001461 | Reject | Included in remote series |
| E8-A | Pool-frequency IDF (incorrect) | Treat candidate-pool term frequency as IDF | 53 | 0.790 | -0.085 | 0.459067 | 4.975 | 0.6025 | 0.653220 | -0.080570 | Reject (reasoning error) | Included in remote series |
| E8-B | Catalog IDF + pool 500 | Weight with catalog-wide `fts5vocab` document frequency | 54 during experiment | 0.845 | -0.030 | 0.522619 | 4.625 | 0.6375 | 0.706786 | -0.027004 | Reject | Included in remote series |
| E8-C | Catalog IDF + pool 100 | Same catalog IDF with the candidate pool kept at 100 | 54 during experiment | 0.860 | -0.015 | 0.540980 | 4.640 | 0.6360 | 0.719494 | -0.014296 | Reject | Included in remote series |
| E9 | Slot conflict resolution | Give each gazetteer term one slot; pool 100 and no IDF | 53 | **0.895** | +0.020 | **0.549056** | **4.215** | 0.6785 | **0.747917** | **+0.014127** | Superseded by E11 | `c1941f6` merge series |
| E10 | Override-routed IDF | If intent-override detected, then route to use IDF over the whole catalogue | 56 | 0.890 | -0.005 | 0.551708 | 4.270 | 0.6730 | 0.745112 | -0.002805 | REJECTED | Included in remote series|
| E11 | Popularity prior | Add `1.2 * log1p(rating_number)` to the rerank score | 58 | **0.965** | +0.070 | **0.662125** | **2.965** | **0.8035** | **0.841838** | **+0.093921** | **Current best** | `52789c4` |
| E13-A | Constraint ledger Stage 0 | Three override-state correctness fixes, measured separately | 103 | 0.965 | +0.000 | 0.662125 | 2.965 | 0.8035 | 0.841838 | +0.000000 | Reject 2 of 3; slot negation guard retained on correctness | Not committed |
| E13-B | Constraint ledger Stage 1 | Append-only entries with status instead of deletion; query projected from active entries | 118 | **0.975** | +0.010 | **0.677881** | **2.810** | 0.8190 | **0.854664** | **+0.012826** | Keep | See branch |
| E13-C1 | Ledger term weighting | Scale answered constraints against volunteered ones in the reranker | 127 | 0.970 | -0.005 | 0.676315 | 2.865 | 0.8135 | 0.850594 | -0.004070 | Reject; validation peaks at the off position | Not committed |
| E13-C | Information-gain probe | Ask an open question after a turn that adds no ledger entry | 127 | **0.980** | +0.005 | **0.698381** | **2.540** | **0.8460** | **0.868714** | **+0.014050** | **Current best** | See branch |
| E14-A | Catalog quality prior | Add `quality_weight * average_rating` to the rerank score | 127 | 0.980 | +0.000 | 0.704938 | 2.540 | 0.8460 | 0.870681 | +0.001967 full, -0.000052 validation | Reject; development and validation argmax disagree | Not committed |

  The E1-A targeted test completed a red-green cycle. The behavior was then
  removed because the evaluator regressed, so it is not in the final test suite
  or a Git commit. The failed result remains in this matrix.

  ## 2. HitRate@10 by scenario

| Method | Buying | Browsing | Intent Override | Boundary |
| --- | ---: | ---: | ---: | ---: |
| E0 Weak BM25 | 0.2375 | 0.0250 | 0.133333 | 0.0000 |
| E1 Field reranker v1 | 0.2375 | 0.0875 | 0.133333 | 0.2000 |
| E1-A + BM25 rank prior | 0.2250 | 0.0875 | 0.133333 | 0.2000 |
| E2 Conversation State v1 | **0.8875** | **0.9625** | **0.533333** | **1.0000** |
| E3-A Fixed clarification | 0.8750 | **0.9625** | 0.566667 | 0.9000 |
| E3-B Profile clarification | **0.8875** | **0.9625** | 0.533333 | **1.0000** |
| E3-C Candidate-aware clarification | 0.8750 | **0.9625** | **0.600000** | 0.9000 |
| E4-A Balanced clarification | **0.8875** | **0.9625** | 0.533333 | **1.0000** |
| E4-B Always-ask-other probe | 0.8875 | **0.9625** | 0.333333 | **1.0000** |
| E5 Slot-aware override memory | 0.8750 | **0.9625** | **0.633333** | 0.9000 |
| E6 Turn-aware override memory | 0.8750 | 0.9625 | 0.633333 | 0.9000 |
| E7 Pool 500 | 0.8625 | 0.9500 | 0.700000 | 0.9000 |
| E8-A Pool-frequency IDF | 0.8125 | 0.8250 | 0.600000 | 0.9000 |
| E8-B Catalog IDF + pool 500 | 0.8625 | 0.8875 | 0.666667 | 0.9000 |
| E8-C Catalog IDF + pool 100 | 0.8625 | 0.9000 | **0.733333** | 0.9000 |
| E9 Slot conflict resolution | 0.8750 | **0.9625** | **0.766667** | 0.9000 |
| E10 Override-routed IDF | 0.8750 | 0.9625 | 0.733333 | 0.9000 |
| E11 Popularity prior | 0.9500 | **1.0000** | **0.933333** | 0.9000 |
| E13-A Stage 0 retained | 0.9500 | **1.0000** | 0.933333 | 0.9000 |
| E13-B Constraint ledger | 0.9500 | **1.0000** | **1.000000** | 0.9000 |
| E13-C Information-gain probe | 0.9500 | **1.0000** | **1.000000** | **1.0000** |

  This table cannot prove private-set performance. It identifies which scenario
  regressed so that an aggregate improvement does not hide a worse user experience.

  ## 3. Diagnostic matrices before implementation

  ### 3.1 First-turn BM25 candidate recall

  Candidate Recall asks whether the target entered a larger candidate pool. It is
  not the official, up-to-ten-turn HitRate@10.

  | Scenario | Sessions | Recall@10 | Recall@50 | Recall@100 | Recall@500 |
  | --- | ---: | ---: | ---: | ---: | ---: |
  | Overall | 200 | 0.185 | 0.380 | 0.525 | 0.860 |
  | Buying | 80 | 0.2375 | 0.4750 | 0.5875 | 0.9375 |
  | Browsing | 80 | 0.0250 | 0.1875 | 0.3625 | 0.7625 |
  | Intent Override | 30 | 0.533333 | 0.666667 | 0.833333 | 0.966667 |
  | Boundary | 10 | 0.0000 | 0.3000 | 0.4000 | 0.7000 |

  Conclusion: the number of targets found grows from 37 in the Top-10 to 172 in
  the Top-500. Ranking is therefore the first measured problem, so the project
  tested a reranker before adding dense retrieval.

  ### 3.2 Catalog field coverage

  | Field | Coverage | Experimental use |
  | --- | ---: | --- |
  | categories | 1.00000 | Main category and broad intent |
  | title | 0.99996 | Highest-weight product matching |
  | details | 0.96660 | Attribute and specification constraints |
  | store | 0.99372 | Supporting brand/store signal |
  | features | 0.89562 | Feature, material, and use-case terms |
  | description | 0.52226 | Lower-weight supporting text |
  | price | 0.21054 | Too sparse for a default hard filter |

  ### 3.3 Public-session target field coverage

  The catalog-wide coverage above does not describe the 200 public-session
  targets exactly. Joining each public `ground_truth.parent_asin` back to the
  frozen catalog matched all 200 sessions to 200 distinct products. Coverage
  uses the same non-empty-field rule as `analysis/catalog_profile.py`.

  | Field | Full catalog | Public targets | Present | Difference |
  | --- | ---: | ---: | ---: | ---: |
  | categories | 1.00000 | 1.000 | 200/200 | +0.000 pp |
  | title | 0.99996 | 1.000 | 200/200 | +0.004 pp |
  | details | 0.96660 | 1.000 | 200/200 | +3.340 pp |
  | store | 0.99372 | 1.000 | 200/200 | +0.628 pp |
  | features | 0.89562 | 1.000 | 200/200 | +10.438 pp |
  | description | 0.52226 | 0.445 | 89/200 | -7.726 pp |
  | price | 0.21054 | **0.890** | **178/200** | **+67.946 pp** |
  | average_rating | 1.00000 | 1.000 | 200/200 | +0.000 pp |
  | rating_number | 1.00000 | 1.000 | 200/200 | +0.000 pp |

  The public targets therefore do not follow the catalog-wide field-presence
  distribution. The largest difference is price: 89.0% of public targets have
  a price, versus 21.054% of the full catalog. Features are also complete on
  the public targets, while description coverage is 7.726 percentage points
  lower than the catalog average.

  The two fields with meaningful missingness vary by scenario:

  | Scenario | Sessions | Price | Description |
  | --- | ---: | ---: | ---: |
  | Buying | 80 | 0.9500 | 0.4875 |
  | Browsing | 80 | 0.8750 | 0.4375 |
  | Intent Override | 30 | 0.766667 | 0.333333 |
  | Boundary | 10 | 0.9000 | 0.5000 |

  Price coverage is therefore high across every scenario, not only Buying.
  This diagnostic measures whether a field is populated; it does not show that
  category values, price ranges, feature contents, or popularity values follow
  the full-catalog distribution. The 200 labeled targets are not a random
  catalog sample, and their coverage must not be assumed to hold for the 800
  private sessions.

  ## 4. Chronological test and experiment record

  ### T0: Reproduce the official baseline

  - Date: 2026-08-29
  - Method: unmodified official weak BM25 starter.
  - Command: `python -m evaluator.local_evaluator`
  - Data: 200 public sessions and 50,000 catalog items.
  - Result: HitRate@10 `0.125`, MRR `0.068034`, MTTC `9.81`, TechnicalScore
    `0.106710`.
  - Purpose: establish the fixed comparison point for every later method.

  ### T1: BM25 candidate recall and catalog coverage

  - Added candidate rank, Recall@10/50/100/500, and per-scenario summaries.
  - Added populated/missing statistics for catalog fields.
  - Automatic tests increased from 3 to 7.
  - Commands:

    ```powershell
    python -m scripts.analyze_bm25_recall
    python -m scripts.analyze_catalog
    python -m unittest discover -s tests -v
    ```

  - Conclusion: test lightweight reranking over Top-100/500 candidates first.
  - Commits: `583e79c`, `e33c097`, `c51573a`, `c438628`.
  - Detailed evidence: [baseline diagnostic summary](../reports/baseline/diagnostic-summary.md).

  ### T2: Field reranker v1

  - Expanded the BM25 candidate pool from 10 to 100.
  - Counted only the highest-value field match for each query term: title `4.0`,
    categories `3.0`, features/details `2.0`, store `1.5`, description `1.0`.
  - Preserved original BM25 order when scores tied.
  - Added reranker unit tests and a real SQLite FTS5 integration test using TDD.
  - Automatic tests increased from 7 to 10.
  - Result: HitRate@10 `0.160`, TechnicalScore `0.133825`.
  - Decision: Keep.
  - Commit: `db65ad2`.
  - Detailed evidence: [local reranker v1](../reports/experiments/local-reranker-v1.md).

  ### T3: BM25 rank-prior ablation

  - Hypothesis: retaining part of the BM25 order could recover five E1 losses.
  - Change: added a bonus that decreases with original BM25 rank.
  - Result: HitRate@10 `0.155`, TechnicalScore `0.129498`, below E1.
  - Decision: Reject; remove the code and the test that protected only the failed behavior.
  - Commit: none. Results remain in the E1 report and this ledger.

  ### T4: Conversation State v1

  - Accumulated valid query constraints across turns.
  - Excluded explicit no-preference replies from query terms.
  - Cleared old constraints when the user overrode the earlier intent.
  - Used anonymized profile tags for non-repeating ask-attribute order.
  - Returned a clarification question and Top-10 recommendations on every turn.
  - Added four conversation behavior tests with TDD.
  - Automatic tests increased from 10 to 14.
  - Leakage check: `starter/` does not reference `ground_truth`, `public_set`,
    `intent_card`, or evaluator behavior fields.
  - Result: HitRate@10 `0.870`, TechnicalScore `0.723824`.
  - Decision: Keep; it was later replaced by E3-C as the best method.
  - Commit: `d770b6f`.
  - Detailed evidence: [conversation state v1](../reports/experiments/conversation-state-v1.md).

  ### T5: Reproduce results in an isolated worktree

  - Created `experiment/clarification-ablation` from `d770b6f`.
  - Reused the same `data/catalog.jsonl` through a hard link.
  - 14/14 tests passed.
  - The full evaluator reproduced HitRate@10 `0.870`, MRR `0.533748`, MTTC
    `4.565`, and TechnicalScore `0.723824`.
  - Conclusion: the experiment environment matched the stable branch and was
    ready for clarification ablation.

  ### T6: Fixed split and clarification-policy ablation

  - Date: 2026-08-29.
  - Used seed `techjam-clarification-v1` to split the public set by scenario and
    difficulty into 120 development and 80 validation sessions.
  - Compared fixed, profile, and candidate policies while keeping retrieval,
    ranking, and state logic unchanged.
  - Selection rule: choose only by validation TechnicalScore.
  - Validation scores: fixed `0.750158`, profile `0.741824`, candidate `0.755720`.
  - Decision: candidate wins and becomes default; fixed is rejected and profile
    remains available as an ablation baseline.
  - Full public: HitRate@10 `0.870`, MRR `0.544236`, MTTC `4.410`,
    TechnicalScore `0.730071`.
  - Implementation commit: `fa84de2`.
  - Detailed evidence: [clarification policy ablation](../reports/experiments/clarification-ablation.md).

  ### T7: Candidate-policy performance rerun

  - First full run: candidate `144.189s`, profile `82.447s`.
  - Optimization: tokenize each candidate once and reuse the token set for all six
    attributes.
  - Optimized candidate run: `88.492s`, with every metric unchanged.
  - Automatic tests increased to 21; an integration test locks the default Agent
    to the candidate policy.
  - The official evaluator entry point reproduced TechnicalScore `0.730071`.

  ### T8: Balanced clarification ablation

  - Date: 2026-08-29.
  - Reason: on full public, E3-C found one fewer Buying and one fewer Boundary
    target than profile.
  - Read-only reruns tied the failures to a generic material answer and a Boundary
    first-turn no-preference response that spent an important question.
  - Method: first ask about a profile preference when it also varies across the
    current candidates; otherwise use candidate order.
  - TDD: added two tests for prioritizing a varied preference and skipping a
    preference with no candidate variation; 23/23 tests passed during the experiment.
  - Validation: Candidate `0.755720`, Balanced `0.743074`, down `0.012646`.
  - Full public: Balanced recovered one Buying and one Boundary hit but lost two
    Intent Override hits; TechnicalScore fell from `0.730071` to `0.725074`.
  - Decision: Reject; Candidate remains the default. The exact rejected code and
    tests are preserved on `review/balanced-clarification-implementation`.
  - Detailed evidence: [balanced clarification experiment](../reports/experiments/balanced-clarification.md).

  ### T9: Always-ask-other question ceiling probe

  - Date: 2026-08-29.
  - Hypothesis: the local simulator's `customer_reply` returns up to two undisclosed
    constraints for `other`, but only one for a specific attribute. Always asking
    `other` can therefore estimate the local upper bound of question-policy gains.
  - Observed evaluator behavior: `classify_constraint` can return only budget,
    material, color, size, style, use_case, and feature. `category` and `brand`
    never match, so asking either locally always receives no additional preference.
  - Change: add an `other` clarification policy that always returns `other` and
    ignores the asked set. Retrieval, ranking, and conversation state stay fixed.
  - Result: HitRate@10 `0.840`, MRR `0.522508`, MTTC `3.635`, TechnicalScore
    `0.724052`, below E3-C at `0.730071`.
  - Scenarios: buying `0.8875`, browsing `0.9625`, and boundary `1.0000` are flat
    or slightly better; intent_override falls from `0.600000` to `0.333333`.
  - Mechanism: `other` exhausts the intent card's four constraints in the first two
    turns. When the turn 3/4 override clears state, the simulator has no undisclosed
    information left, so the session cannot recover.
  - Conclusion: question choice is close to saturated for Buying, Browsing, and
    Boundary. The larger bottleneck is Intent Override state handling; both
    policies have MTTC near `8.5` there.
  - Decision: Reject and keep only as a diagnostic. The private simulator is not
    guaranteed to implement `other` in the same way.
  - Commit: not separate from the remote experiment series.
  - Evidence: [clarification-other-probe.json](../reports/experiments/clarification-other-probe.json)

  ### T10: Slot-aware override memory

  - Date: 2026-08-29.
  - Hypothesis: T9 shows that question choice is saturated and the real bottleneck
    is Intent Override state handling. Clearing all constraints also discards the
    product category, so the agent should replace only the slots that changed.
  - Changes:
    - Add `analysis/gazetteer.py` to mine department, category, material, color,
      style, and size vocabularies from the frozen catalog, producing the 19 KB
      `data/gazetteer.json`.
    - Add `starter/slots.py` to assign message terms to slots, preferring the
      longest match.
    - Update `starter/agent.py` to preserve `DURABLE_SLOTS` (category and
      department) during override unless the same message replaces that slot;
      clear the remaining slots.
    - Fall back to an empty vocabulary when the gazetteer is absent or invalid,
      matching E3-C retrieval behavior.
  - Vocabulary coverage versus the previous hand-written constants: material
    `54.7% -> 81.6%`, color `33.3% -> 69.5%`, size `20.9% -> 51.0%`, and style
    `36.5% -> 61.1%`.
  - Automatic tests increased from 35 to 41. The previous override test expected
    all constraints to be cleared, so it was rewritten to require dropping the
    revoked value while preserving category. Temporarily emptying `DURABLE_SLOTS`
    confirmed that the corrected test fails without the behavior. Tests now carry
    their own temporary gazetteer instead of depending on the repository file.
  - Result: HitRate@10 `0.875`, MRR `0.540300`, MTTC `4.290`, TechnicalScore
    `0.733790`, which is `+0.003719` over E3-C at `0.730071`.
  - Scenarios: Buying, Browsing, and Boundary are unchanged. Intent Override rises
    from `0.600000` to `0.633333`, and its MTTC improves from `8.500` to `7.700`.
  - Interpretation: only the intended scenario changes, in the intended direction,
    but `+0.033333` is only one extra hit among 30 Intent Override sessions. MRR
    also falls slightly by `0.003936`, so the evidence is weak.
  - Limitation and next step: the current override keeps durable slots but drops
    answers learned after turn 1 even when the user did not revoke them. Test
    retaining constraints by source turn next.
  - Commit: included in the remote experiment series.

  ### T11: Turn-aware override memory (no measurable effect)

  - Date: 2026-08-29.
  - Hypothesis: E5 keeps only durable slots during override and discards question
    answers learned from turn 2 onward even when the user did not revoke them.
    Preserving by arrival turn may recover more sessions.
  - Change: record the arrival turn for each slot. During override, keep durable
    slots and values with `arrived > 1`; drop volunteered turn-1 preferences and
    slots replaced by the new message.
  - Result: HitRate@10 `0.875`, MRR `0.540300`, MTTC `4.290`, TechnicalScore
    `0.733790`—identical to E5 in every aggregate and scenario metric.
  - Diagnosis across 30 Intent Override sessions: the two rules preserve different
    sets in only four sessions, and none changes hit or rank. Although 23 sessions
    contain a non-durable constraint learned after turn 1, the override message
    usually names that slot, so both rules remove it.
  - Decision: Reject because it has no measured effect. Keep the turn-aware code
    because it better matches the intended meaning and adds no cost, but do not
    claim a score gain.
  - Additional finding: the gazetteer has cross-slot contamination. For example,
    `small` appears in both color and size, producing `'color': {'small': 3}`;
    `women` appears in both department and category.
  - Conclusion: further override-memory tuning is not the next bottleneck. The two
    iterations add only `0.003719`; investigate the gazetteer and retrieval instead.
  - Commit: included in the remote experiment series.

  ### T12: Fix gazetteer cross-slot contamination

  - Date: 2026-08-29.
  - Problem: 27 gazetteer terms belong to more than one slot. Examples include
    `small` in color and size, `women` in department and category, and `hoodie`
    in category and style. A probe shows `'color': {'small': 3}`.
  - Why support count cannot break ties: category counts come from taxonomy nodes
    while attribute counts come from free-text coverage, so they use different
    scales. `silver` also has the same count, 2935, under material and color
    because both are measured against the same text.
  - Method: use fixed source-reliability precedence—`department > material > size
    > category > color > style`—and assign each term to only the highest-priority slot.
  - Result: cross-slot terms fall from 27 to 0 among 842 terms. Spot checks map
    `small -> size`, `silver -> material`, `cotton -> material`, `women -> department`,
    `hoodie -> category`, and `sneaker -> category`.
  - Automatic tests increased to 51.

  ### T13: Candidate-pool and IDF ablations (all rejected)

  - Date: 2026-08-29.
  - Hypothesis: Recall@100 is `0.525` and Recall@500 is `0.860`, so a larger pool
    may improve recall. The reranker also weights rare and common terms equally;
    IDF may improve ordering.
  - E7, pool 500: TechnicalScore `0.732329`, below pool 100 at `0.733790`.
    Intent Override rises from `0.633333` to `0.700000`, but Browsing and Buying
    each lose one session and MRR falls by `0.011538`.
  - E8-A, incorrect implementation: computing IDF from the candidate pool drops
    TechnicalScore to `0.653220`. The candidate pool already contains documents
    matched by the query, so its most useful term appears in most candidates and
    is incorrectly downweighted. IDF must be computed over the whole catalog.
  - E8-B/E8-C, correct implementation: use `fts5vocab` catalog document frequency.
    Pool 500 scores `0.706786`; pool 100 scores `0.719494`. Both trail `0.733790`.
  - Two-by-two comparison:

    | | No IDF | Catalog IDF |
    | --- | ---: | ---: |
    | pool 100 | **0.733790** | 0.719494 |
    | pool 500 | 0.732329 | 0.706786 |

  - Key observation: both changes improve Intent Override but damage Browsing.
    E8-C reaches Intent Override `0.733333`, up three hits from `0.633333`, while
    Browsing falls from `0.9625` to `0.9000`, down five hits. With 80 Browsing
    sessions and only 30 Intent Override sessions, Browsing losses dominate.
  - Decision: reject E7 and E8-A/B/C; restore pool 100 with no IDF. Keep the tested
    optional `idf` argument in `rerank_candidates` for later routing experiments.
  - Next step: test scenario routing because the agent can observe an override and
    change retrieval only after that turn. No gain is assumed in advance.
  - Commit: included in the remote experiment series.

  ### T14: Measure the clean gazetteer independently (current best)

  - Date: 2026-08-29.
  - Background: E5/E6 were measured with a contaminated gazetteer. After T12 fixed
    it, no isolated pool-100/no-IDF run was made because E7/E8 failures obscured it.
  - Configuration: pool 100, no IDF, clean gazetteer. The only behavior difference
    from E6 is the gazetteer.
  - Result: HitRate@10 `0.895`, MRR `0.549056`, MTTC `4.215`, TechnicalScore
    `0.747917`, which is `+0.014127` over E6 at `0.733790`.
  - Scenarios: Intent Override rises from `0.633333` to `0.766667`, four extra hits.
    Browsing `0.9625`, Buying `0.8750`, and Boundary `0.9000` do not regress.
  - Interpretation: contamination itself damaged override logic. When `small` was
    classified as color, a size answer marked color as replaced and discarded a
    real color constraint. When `women` was also category, a gender mention could
    clear category. E5/E6 applied better memory logic to incorrect slot data;
    fixing the data released the intended gain.
  - Cumulative change from E3-C: TechnicalScore `0.730071 -> 0.747917`
    (`+0.017846`) and Intent Override `0.600000 -> 0.766667`, five extra hits.
  - Limitation: this is still the 200-session public set, including only 30 Intent
    Override sessions. Private-set behavior is unverified.
  - Commit: merged to remote main in `c1941f6`.

- Date: 2026-08-29
- Hypothesis: T12's 2x2 shows IDF improves intent_override but hurts browsing. Browsing never sends
  override, so by placing IDF behind the agent's own observable signal of "override detected,"
  we should be able to capture the gain without paying the cost.
- Change: `_session_override_seen` records per-session whether an override has appeared; once it
  appears, rerank for the rest of that session is passed `_catalog_idf`, otherwise it's passed `None`.
- Route isolation verified: boundary `0.9000`, browsing `0.9625`, buying `0.8750`
  are **identical item-for-item** to E9, and MTTC is also identical. The branch only fires
  where it's supposed to.
- Result: intent_override `0.766667 -> 0.733333` (one fewer hit),
  MTTC `7.200 -> 7.567`, TechnicalScore `0.747917 -> 0.745112`.
- Key evidence: intent_override under IDF is `0.733333` on both **contaminated gazetteer** (E8-C)
  and **clean gazetteer** (E10) — exactly the same; whereas the no-IDF baseline, after fixing the
  contamination, rises from `0.633333` to `0.766667`. This shows IDF is not an additive gain but a
  **substitute** for the contamination fix: both are correcting the same problem (indiscriminate
  words getting equal weight). Once the slots are clean, IDF has nothing left to do — it just
  reimposes its own ceiling.
- Side observation: MRR actually rises `+0.002652` while HitRate drops. When IDF hits, it ranks
  higher — but there are fewer hits. It shifts weight toward rare words: a gain when the word
  matches, nothing when it doesn't.
- Decision: retire it. The routing mechanism itself is correct and clean; the problem is that IDF
  adds no incremental value for this task. Reverted — `starter/agent.py` is now byte-identical to E9.
- Commit: not committed (record only).

### T15: Popularity prior (current best)

- Date: 2026-08-29
- Origin: a completely failed Intent Override session. All ten returned products satisfied
  every disclosed constraint — leather, buckle, belt — so nothing separated them and ties fell
  back to BM25 order. Target `B071X54486` has 6,614 ratings; eight of the ten returned items
  had between 10 and 257.
- Key measurement: the hidden target is a **real purchase record**, and purchased items are
  reviewed items.

  | | Catalog | Targets |
  | --- | ---: | ---: |
  | Median `rating_number` | 12 | **6,846** |

  The median target sits at the **99.5th percentile** of catalog popularity. 193/200 targets
  fall in the top quartile, 173/200 in the top decile, only 2/200 in the bottom quartile.
  The field has 100% coverage and was previously unused.
- Change: the rerank score gains `popularity_weight * log1p(rating_number)`. `rating_number`
  is collected into a separate dict during index construction rather than added to the FTS5
  table, so the `bm25()` column weights are untouched. A missing value contributes zero.
- Degeneracy check: an agent that ignores the conversation entirely and returns the globally
  most-reviewed products every turn scores HitRate@10 **0.035** (7/200). Retrieval narrows
  50,000 products to a few hundred; popularity orders that set. The two are complementary,
  and popularity is not substituting for conversational understanding.
- Weight sweep on the same seed and 80-session validation split as the clarification ablation,
  choosing on validation only:

  | Weight | Validation | Development | Full | Boundary |
  | ---: | ---: | ---: | ---: | ---: |
  | 0.0 | 0.771539 | 0.732169 | 0.747917 | 0.9000 |
  | 0.5 | 0.830092 | 0.810395 | 0.818274 | 0.9000 |
  | 0.8 | 0.837653 | 0.824992 | 0.830057 | 0.9000 |
  | **1.2** | **0.844722** | **0.839915** | **0.841838** | 0.9000 |
  | 1.8 | 0.838857 | 0.828661 | 0.832739 | 0.9000 |
  | 2.5 | 0.821893 | 0.821475 | 0.821642 | 0.9000 |
  | 8.0 | 0.773765 | 0.777014 | 0.775714 | **0.8000** |
  | 16.0 | 0.755640 | 0.749870 | 0.752178 | **0.8000** |

  A clean inverted U. Development and validation peak at `1.2` **independently**, and 0.8-1.8
  is a plateau rather than a spike. At weight >= 8 Boundary drops from `0.9000` to `0.8000`:
  the failure mode where popularity overwhelms constraint matching is real, but appears only
  well past the peak.
- Result: HitRate@10 `0.965`, MRR `0.662125`, MTTC `2.965`, TechnicalScore `0.841838`
  (E9 was `0.747917`, `+0.093921`).
- Every scenario improved or held: buying `0.8750 -> 0.9500`, browsing `0.9625 -> 1.0000`,
  intent_override `0.766667 -> 0.933333`, boundary `0.9000` unchanged but faster.
- Limitations: the weight is tuned on 200 public sessions; if the private set draws targets
  with a different popularity profile the optimum moves. `1.2` was chosen because it sits
  mid-plateau, not because it is the argmax. This is a prior about **how the dataset was
  constructed**, not personalization, and the report should say so. Boundary is unchanged at
  `0.9000` across every weight, so those sessions are limited by something else.
- Commit: `52789c4`. Evidence: [popularity prior](../reports/experiments/popularity-prior.md).

### T16: Coverage-stress dual evaluation (diagnostic environment)

- Date: 2026-08-30.
- Commands: `python -m scripts.build_coverage_stress_catalog` and
  `python -m scripts.run_dual_catalog_evaluation --output reports\\experiments\\coverage-stress-baseline.json`.
- Construction: all 50,000 catalog rows and all 200 distinct public targets
  matched. Target coverage changed from original to stress as follows: details
  `200 -> 193` (7 masked), store `200 -> 199` (1), features `200 -> 179` (21),
  description `89 -> 89` (15 unfillable shortfall), and price `178 -> 42` (136);
  title, categories, average rating, and rating count remain `200/200`.
- Tests: 88 automated tests passed before and after generation. The generated
  catalog hash was `f0a1e6381f613409fee279db7d25f6b7603e46f6952b2ae7f3c10635447630a5`
  on two consecutive builds. Identifier order, non-target records, planned
  counts, and no-fill invariants passed.
- Official overall: HitRate@10 `0.965`, MRR `0.662125`, MTTC `2.965`,
  Efficiency `0.8035`, TechnicalScore `0.841838`. Coverage-stress overall:
  `0.965`, `0.682284`, `2.915`, `0.8085`, `0.848885`; deltas are `+0.000`,
  `+0.020159`, `-0.050`, `+0.0050`, and `+0.007047` respectively.
- Scenarios (official -> stress, HitRate@10 / MRR / MTTC): Buying
  `0.9500 / 0.696905 / 2.2875 -> 0.9500 / 0.714940 / 2.2750`; Browsing
  `1.0000 / 0.665595 / 2.8250 -> 1.0000 / 0.688408 / 2.7625`; Intent Override
  `0.933333 / 0.587685 / 4.933333 -> 0.933333 / 0.601852 / 4.933333`; Boundary
  `0.9000 / 0.579444 / 3.6000 -> 0.9000 / 0.613333 / 3.2000`.
- Smoke checks: both `python -m scripts.run_clarification_ablation --policies candidate`
  and `python -m scripts.run_popularity_sweep --weights 1.2` emitted official,
  coverage-stress, and delta payloads.
- Decision: keep this as a diagnostic evaluation environment, not an Agent
  method. Official metrics remain primary. Stress changes retrieval-visible
  metadata and evaluator-materialized customer disclosures, matches marginal
  presence only, leaves description at `89/200` because filling is forbidden,
  does not correct public-target popularity bias, and cannot forecast private
  results.
- Evidence: [manifest](../reports/experiments/coverage-stress-catalog.json),
  [dual result](../reports/experiments/coverage-stress-baseline.json),
  [report](../reports/experiments/coverage-stress-dual-evaluation.md),
  [design](designs/2026-08-29-coverage-stress-dual-evaluation-design.md), and
  [plan](plans/2026-08-29-coverage-stress-dual-evaluation.md).

### T17: Constraint ledger Stage 0, override-state correctness (rejected)

- Date: 2026-08-30
- Hypothesis: `scripts/trace_session` showed that 26 of 30 intent_override
  sessions already rank the target inside the Top-10 before the override, and
  that 6 lose it at the override turn. Three defects were held responsible:
  the override rebuilds the term list from singular gazetteer forms, the
  override sentence's own words enter the query permanently, and the
  no-preference guard covers `_constraint_terms` but not `extract_slots`.
- Method: each fix implemented with a targeted test that fails against E11 for
  its stated reason, then measured alone and in combination.
- Ablation validation TechnicalScore: none (E11) `0.844722`, surface form
  `0.843524`, stopwords `0.837149`, slot guard `0.844722`, surface+guard
  `0.843430`, all three `0.839274`.
- Key finding: removing conversational filler *costs* two intent_override
  sessions. Those terms widen the FTS5 `MATCH` expression and change which
  hundred documents enter the candidate pool, while contributing nothing in
  the reranker. The pipeline depends on query width, not query cleanliness.
- Decision: reject surface-form preservation and the stopword set; retain the
  slot negation guard, which is exactly score-neutral, on correctness grounds.
  Rejected code and tests removed per the T3 precedent.
- Limitation: the full set and the validation split disagree in sign for the
  combined arm (`+0.001963` full, `-0.005448` validation). These differences
  sit near the noise floor of a 200-session set.
- Evidence: [Stage 0 report](../reports/experiments/constraint-ledger-stage0.md).

### T18: Constraint ledger Stage 1, append-only state and query projection (keep)

- Date: 2026-08-30
- Change: `_session_terms` removed from the scored path. Every token becomes a
  ledger entry carrying its own surface form, normalized form, slot or `null`,
  status, source, and first and last turn. An override sets statuses; nothing
  is deleted, so the term list is never rebuilt. The query is projected from
  the active entries each turn. E11's three override rules are unchanged; they
  are applied to entries rather than to slot-dictionary keys, which is what
  gives an unclassified token a `first_turn` of its own.
- Stage 0 shaped two requirements: `slot=None` entries are projected like any
  other active entry, and surface forms are projected rather than gazetteer
  singulars.
- Overall: HitRate@10 `0.975`, MRR `0.677881`, MTTC `2.810`, Efficiency
  `0.8190`, TechnicalScore `0.854664`; validation `0.853190`.
- Scenarios: Buying `0.950000`, Browsing `1.000000`, Boundary `0.900000`,
  Intent Override `0.933333 -> 1.000000`. Three of four scenarios are identical
  to the last decimal, which is the evidence that the change touches only what
  it claims to.
- Structural invariants: query width never falls below E11's at the same turn
  (0 violations in 200 sessions); normalization losses across the 30 override
  turns fall from 54 to 3, and all three residuals are cases where the override
  message itself restates the term in singular.
- The originally specified invariant, "zero query terms lost at the override
  turn", was mis-specified and is corrected in the design: an override is a
  revocation, so the constraints it revokes must leave the query.
- Decision: keep. `state_model="slots"` remains the constructor default and
  reproduces E11 at `0.841838` / `0.844722`.
- Evidence: [Stage 1 report](../reports/experiments/constraint-ledger-stage1.md).

### T19: Constraint ledger Stage 2, weighting and the information-gain probe

- Date: 2026-08-30
- E13-C1, term weighting by source: the ledger records whether a constraint was
  volunteered or answered; `answered_weight` scales the latter in the reranker.
  Validation by weight: `0.6` `0.836582`, `1.0` (off) `0.853190`, `1.2`
  `0.851524`, `1.5` `0.850040`. The optimum is the off position on both sides.
  Reject. `term_weights` and `ConstraintLedger.projection_weights` are retained
  as no-ops at their defaults, per the T13 precedent that kept `idf`.
  `decay_lambda` stays `0` and was never swept: the public set contains no
  signal from which to fit a decay rate.
- E13-C, information-gain probe: retrieval is a pure function of the projected
  terms, so a turn adding no active entry cannot change the ranking. After `K`
  consecutive such turns the agent asks an open question instead of continuing
  down the attribute order. Validation by threshold: `0` `0.858051`, `1`
  `0.867378`, `2` `0.857690`, `3` `0.854190`.
- `K = 0` is T9's rejected always-ask-`other` probe. It has the best
  development score of any configuration and a validation score `0.009327`
  below `K = 1`, and is the only configuration that loses an intent_override
  session. Selection used validation alone.
- Result at `K = 1`: HitRate@10 `0.980`, MRR `0.698381`, MTTC `2.540`,
  Efficiency `0.8460`, TechnicalScore `0.868714`; validation `0.867378`.
- Boundary moves from `0.900000` to `1.000000`. It had been unchanged through
  every popularity weight in T15 and through Stages 0 and 1. A boundary session
  is one where every reply adds nothing, which is exactly the probe's trigger.
- Dead turns: `163/586` at E11, `140/557` at E13-B, `85/504` at E13-C. The count
  of sessions containing a dead turn is unchanged at 57, correctly: the probe
  cannot prevent the first one, because that turn is the signal.
- Limitation: this is the experiment most exposed to the simulator. The gain
  depends on the evaluator answering `other` with up to two undisclosed
  constraints, which T9 documented and warned may not hold privately. The
  mechanism is a general strategy; the size of the gain is not guaranteed to
  transfer. If the private simulator treats `other` like any other attribute,
  this degrades toward E13-B rather than breaking.
- Evidence: [Stage 2 report](../reports/experiments/constraint-ledger-stage2.md).

### T20: Rank-margin diagnostic and the catalog quality prior (rejected)

- Date: 2026-08-30
- Purpose: with HitRate@10 at `0.980`, decide whether the remaining effort
  belongs to recall or to ranking. Rank distribution over 200 sessions: 114 at
  rank 1, 30 at rank 2, 10 at rank 3, 42 at ranks 4-10, 4 missed. Moving every
  hit to rank 1 is worth `+0.084486`; finding all four misses is worth
  `+0.010000`. Ranking headroom is 8.4x recall headroom.
- The four Buying misses are one recall failure and three ranking failures.
  `public_0020` carries a single review and never enters the Top-100 pool; it
  is the documented cost of the popularity prior. The other three sit at pool
  positions 11, 17 and 28 the whole time and share a shape: every hard
  constraint is a generic material word.
- Of 40 sessions hitting at rank 2 or 3, 23 are decided by popularity rather
  than by matching. Median score gap to rank 1 is `0.669`, minimum `0.003`, and
  23 of 40 gaps are below one field-weight unit.
- E14-A: `average_rating` has full catalog coverage and appeared in no scored
  path. Target median sits at the 66.8th catalog percentile against the 99.5th
  for `rating_number`; only 16/200 targets rate below 4.0 against 32.6% of the
  catalog. Validation by weight: `0.0` `0.867378`, `0.5` `0.865258`, `1.0`
  `0.867326`, `2.0` `0.868299`. Reject: the range is `0.003`, non-monotone,
  with no plateau, and development and validation argmax disagree outright.
  Code removed.
- Consequence for sequencing: the near-ties are not breakable by catalog
  metadata, and `average_rating` was the last unused fully covered field. E12's
  Gate 1 measures first-turn Recall@100, which limits one session of 200 and is
  structurally unable to distinguish rank 2 from rank 1. If E12 is run, that
  gate should be restated to measure rank quality. A re-measurement of IDF under
  the clean gazetteer and ledger is a hypothesis worth testing, not a prediction.
- Evidence: [rank-margin diagnostic](../reports/experiments/rank-margin-diagnostic.md).

  ## 5. Current automated test coverage

  | Test module | Tests | Behavior protected |
  | --- | ---: | --- |
  | `test_evaluator.py` | 3 | Output normalization, miss turn, hidden-field materialization |
  | `test_bm25_diagnostics.py` | 3 | Rank, cutoff recall, first-turn measurement |
  | `test_catalog_profile.py` | 1 | Coverage meaning for empty collections |
  | `test_reranker.py` | 4 | Complete-constraint priority, BM25 tie order, and optional catalog IDF |
  | `test_agent_reranking.py` | 1 | Agent reranks a larger candidate pool |
  | `test_conversation_state.py` | 14 | Accumulation, negation, slot-aware override, fallback behavior, policy selection and default |
  | `test_clarification.py` | 3 | Fixed/profile difference, candidate grounded-attribute selection, and `other` probe |
  | `test_clarification_ablation.py` | 1 | Multiple policies and splits on the real FTS5 evaluator |
  | `test_experiment_split.py` | 1 | Fixed split size, stratification, and no dev/validation overlap |
  | `test_experiment_results.py` | 1 | Split metrics, scenario metrics, and TechnicalScore |
  | `test_gazetteer.py` | 16 | Vocabulary mining, normalization, coverage, and one-slot precedence |
  | `test_slots.py` | 5 | Whole-word, singular/plural, longest-match, and slot assignment behavior |
  | `test_ledger.py` | 27 | Slot assignment, `slot=None` survival, status transitions, restatement, projection order and cap, weights, probe thresholds, slot/ledger equivalence |
| `test_session_trace.py` | 13 | Override keep/drop classification, normalization loss, dead-turn detection, trace/evaluator agreement |
| **Total** | **127** | Current full regression suite |

The per-module counts for the older modules have drifted as experiments were
added. The authoritative number is whatever `python -m unittest discover -s
tests` reports.

  Run the full tests:

  ```powershell
  python -m unittest discover -s tests -v
  ```

  Run the official public evaluator:

  ```powershell
  python -m evaluator.local_evaluator
  ```

  ## 6. How to update this ledger

  Follow the full [experiment workflow](EXPERIMENT_WORKFLOW.md). For every method:

  1. Assign the next ID, such as `E10`; use `E10-A` and `E10-B` for variants.
  2. Add a method-matrix row even when the result fails.
  3. Add Buying, Browsing, Intent Override, and Boundary to the scenario matrix.
  4. Add a chronological entry with the hypothesis, change, commands, test count,
    metrics, decision, and commit or review branch.
  5. Store only aggregate metrics. Never record private labels or credentials.
  6. For a rejected method, state which retained method beat it and by how much.
  7. Update "Current best" at the top without overwriting historical results.
  8. Update the local Chinese mirror, but never stage or push it.

  New experiment template:

  ```markdown
  ### T<N>: <Experiment name>

  - Date: YYYY-MM-DD
  - Hypothesis:
  - Change from the last retained method:
  - New or changed tests:
  - Commands:
  - Overall: HitRate@10, MRR, MTTC, Efficiency, TechnicalScore
  - Scenarios: Buying, Browsing, Intent Override, Boundary
  - Decision: Keep / Reject / Need more evidence
  - Commit or review branch:
  - Limitations and next step:
  ```

  ## 7. Metric meanings and comparison rules

  - **HitRate@10:** share of sessions that find the target within ten turns; higher
    is better.
  - **MRR:** average reciprocal target rank; higher means the target appears nearer
    the top.
  - **MTTC:** average first-hit turn, with a miss counted as turn 11; lower is better.
  - **Efficiency:** `clip((11 - MTTC) / 10, 0, 1)`.
  - **TechnicalScore:** `0.50 × HitRate + 0.30 × MRR + 0.20 × Efficiency`.
  - Candidate Recall and official HitRate@10 are not directly comparable.
  - Public-set improvement does not guarantee private-set improvement. Keep failed
    experiments and ablation evidence.

  ## 8. Evidence sources

- [Official baseline JSON](baseline_results.json)
- [Evaluation configuration](evaluation_config.json)
- [Baseline diagnostics](../reports/baseline/diagnostic-summary.md)
- [Field reranker experiment](../reports/experiments/local-reranker-v1.md)
- [Conversation state experiment](../reports/experiments/conversation-state-v1.md)
- [Clarification policy ablation](../reports/experiments/clarification-ablation.md)
- [Balanced clarification experiment](../reports/experiments/balanced-clarification.md)
- [Slot memory and retrieval ablation](../reports/experiments/slot-memory-and-retrieval-ablation.md)
- [Popularity prior](../reports/experiments/popularity-prior.md)
- [Adaptive retrieval design](superpowers/specs/2026-08-29-adaptive-intent-aware-retrieval-design.md)
- [Constraint ledger design](designs/2026-08-30-constraint-ledger-design.md)
- [Constraint ledger Stage 0](../reports/experiments/constraint-ledger-stage0.md)
- [Constraint ledger Stage 1](../reports/experiments/constraint-ledger-stage1.md)
- [Constraint ledger Stage 2](../reports/experiments/constraint-ledger-stage2.md)
- [Rank-margin diagnostic](../reports/experiments/rank-margin-diagnostic.md)
