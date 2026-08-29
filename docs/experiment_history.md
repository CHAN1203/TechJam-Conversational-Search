  # Experiment History and Method Comparison Matrix

  This file is the project's experiment ledger. Every change to retrieval,
  ranking, conversation state, or question policy must add a result here,
  including failed experiments. It should answer three questions directly:

  1. Where did the project start?
  2. What changed in each experiment?
  3. Which method is best, and why was each method kept or rejected?

> Current best: E13 Buying/Browsing Routing, with public HitRate@10 `0.970`,
> MRR `0.671744`, MTTC `2.930`, and TechnicalScore `0.847923`.
>
> E15 was reverted after review: its result is not an improvement on any
> measurable metric (0/200 public sessions differ from E13). Its only
> claimed value was an unverifiable bet that the private set phrases an
> override differently than the public simulator's one fixed sentence --
> real added state and logic for a risk that cannot be confirmed from here.
> That is a judgment call about risk tolerance, not evidence of being
> "better," and calling it a "clean win" during review overstated it.
> Preserved on `review/narrow-phrase-independent-override-implementation`
> in case that judgment call is revisited later.

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
| E11 | Popularity prior | Add `1.2 * log1p(rating_number)` to the rerank score | 58 | **0.965** | +0.070 | **0.662125** | **2.965** | **0.8035** | **0.841838** | **+0.093921** | Superseded by E13 | `52789c4` |
| E12 | Phrase-independent override | Trigger override on a same-slot value conflict, not only the literal simulator sentence | 77 | 0.960 | -0.005 | 0.661292 | 3.005 | 0.7995 | 0.838288 | -0.003550 | Reject (design tradeoff, see report) | Review branch |
| E13 | Buying/Browsing routing | Classify route at turn 1; reward candidates matching every known constraint, Buying sessions only | 79 | **0.970** | +0.005 | **0.671744** | **2.930** | **0.8070** | **0.847923** | **+0.006085** | **Current best** | Local, not pushed |
| E14 | Expected-value clarification | Score each attribute by Shannon entropy of its value split, not coverage*diversity | 86 | 0.975 | +0.005 | 0.670619 | 3.060 | 0.7940 | 0.847486 | -0.000437 | Reject (close; validation split agrees) | Review branch |
| E15 | Narrow phrase-independent override | Override trigger only on a conflict with a slot value legitimately established for its own question | 90 | 0.970 | +0.000 | 0.671744 | 2.930 | 0.8070 | 0.847923 | +0.000000 | Reverted on review -- see note above matrix | `review/narrow-phrase-independent-override-implementation` |
| E16 | Dense retrieval (standalone) | TF-IDF + Truncated SVD replaces BM25 entirely, isolated comparison | 93 | 0.665 | -0.305 | 0.534054 | 5.625 | 0.5375 | 0.600216 | -0.247707 | Reject as standalone; feeds E17 | Local, not pushed |

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
| E12 Phrase-independent override | 0.9500 | 0.9875 | **0.933333** | 0.9000 |
| E13 Buying/Browsing routing | **0.9625** | **1.0000** | **0.933333** | 0.9000 |
| E14 Expected-value clarification | 0.9625 | 1.0000 | **0.966667** | 0.9000 |
| E15 Narrow phrase-independent override | **0.9625** | **1.0000** | **0.933333** | 0.9000 |
| E16 Dense retrieval (standalone) | 0.6750 | 0.6750 | 0.633333 | 0.6000 |

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

### T16: Phrase-independent override (rejected, design tradeoff)

- Date: 2026-08-29
- Origin: `_is_intent_override()` matches one literal sentence copied from the
  local simulator's `behavior_for()` template. This was already flagged as a
  limitation in T14/`slot-memory-and-retrieval-ablation.md`: the private set
  is not guaranteed to phrase a change of mind the same way.
- Hypothesis: a slot already holding one value, and the current message
  supplying a *different* value for that same non-durable slot, is itself
  evidence of a change of mind — independent of sentence wording.
- Change: `_is_intent_override()` gains a second, additive path to `True`
  (a same-slot conflict) alongside the existing literal-phrase check. The
  override *mechanism* (which slots survive, which are cleared) is
  unchanged; only the *trigger* is broadened.
- New tests: 4, in `tests/test_conversation_state.py`
  (`PhraseIndependentOverrideTest`) — new-behavior, two false-positive
  guards, and a literal-phrase regression guard. All red-green verified.
- Commands:

  ```powershell
  python -m unittest discover -s tests -v
  python -m evaluator.local_evaluator
  ```

- Result: HitRate@10 `0.960`, MRR `0.661292`, MTTC `3.005`, TechnicalScore
  `0.838288` (E11 was `0.841838`, `-0.003550`).
- Scenario: buying `0.9500` unchanged, browsing `1.0000 -> 0.9875` (one
  session), intent_override `0.933333` unchanged, boundary `0.9000`
  unchanged.
- Root cause of the one regression, traced turn by turn on `public_0172`:
  the gazetteer correctly mines `synthetic` as a **material** term, but the
  simulator disclosed it in answer to a `feature` question, not a
  `material` question. A later, real `material` answer (`cotton`) then
  looks like a conflict with `synthetic` and triggers the broadened
  override, which — correctly, by design — replaces the slot's contents and
  drops `synthetic` from the search. The baseline kept both words and found
  the target at rank 6; this version does not. This is a design weakness
  (the rule cannot distinguish "new answer to the same question" from "new
  answer to a different question that shares a gazetteer slot"), not an
  implementation bug — the code does exactly what the rule says.
- Decision: **Reject as the default.** The threshold set before
  implementation (full-set TechnicalScore must not drop below `0.841838`)
  is not met. The cost is small (one session) and the benefit (robustness
  to a differently-worded override on the private set) is real but
  unmeasurable on this public set, so this is a judgment call on risk
  tolerance rather than a clean-cut rejection — left to the project owner.
- Commit/branch: `review/phrase-independent-override-implementation`
  (implementation and tests preserved, not merged into the default agent
  configuration).
- Limitations and next step: a narrower version — only trust the broadened
  trigger when the conflicting slot is the one the agent's own previous
  `ask_attribute` was actually about, rather than any accumulated slot —
  would have avoided this exact false positive without losing the
  paraphrase robustness. Deliberately not attempted here, to keep this
  experiment to one idea; it requires plumbing the previous turn's
  `ask_attribute` into `respond()`. Evidence:
  [phrase-independent override](../reports/experiments/phrase-independent-override.md).

### T17: Buying/Browsing routing (current best)

- Date: 2026-08-29
- Origin: `TechJam.docx` lists Intent-Aware Routing (Buying vs. Browsing) as
  an unimplemented Layer 3 option. This project's own T13
  (`slot-memory-and-retrieval-ablation.md`) had already measured that every
  setting which helped Intent Override (pool 500, catalog IDF) hurt
  Browsing, and named routing -- untried until now -- as the way out of
  that tradeoff.
- Hypothesis: a Buying customer discloses a concrete constraint on the
  opening turn (`docs/competition_specification.md`). E1's field-weighted
  reranker already rewards matching more terms, but treats every term
  independently, so a candidate with several cheap, tangential matches can
  outscore one that satisfies every constraint actually stated. Classify
  the session once, at turn 1, and reward complete constraint matches only
  on that path.
- Change: `_classify_route()` in `starter/agent.py`, called once at turn 1
  from the `message_slots` already computed that turn, cached per session.
  Buying sessions pass `required_terms` (this turn's known non-durable slot
  terms, intersected with the actual query terms) and
  `completeness_bonus=4.0` to `rerank_candidates`; Browsing sessions pass
  neither, which is a no-op by construction. `starter/reranker.py` gains
  `required_terms`/`completeness_bonus`, read off the same per-term field
  weights already computed for scoring -- no second text scan.
- New tests: 10 (4 in `test_reranker.py::CompletenessBonusTest`, 6 in
  `test_conversation_state.py::BuyingBrowsingRoutingTest`), covering
  classification, freezing at turn 1, the reranker mechanism in isolation,
  and an end-to-end ranking-flip test. All red-green verified.
- Commands:

  ```powershell
  python -m unittest discover -s tests -v
  python -m evaluator.local_evaluator
  ```

- Result: HitRate@10 `0.970`, MRR `0.671744`, MTTC `2.930`, TechnicalScore
  `0.847923` (E11 was `0.841838`, `+0.006085`).
- Scenario: buying `0.9500 -> 0.9625` (one more session; MRR also rises,
  `0.696905 -> 0.720952` -- items already found now rank higher too).
  Browsing `1.0000`, intent_override `0.933333`, boundary `0.9000` are all
  **identical to E11 down to the last digit** -- not a coincidence, the
  intended isolation: those sessions classify as Browsing, where the bonus
  never fires.
- Decision: **Keep. New current best.** Every scenario holds or improves;
  none regresses at all.
- Commit/branch: local commit on `experiment/buying-browsing-routing`, not
  pushed to the shared remote.
- Limitations and next step: the bonus weight (`4.0`) is one reasoned value,
  not swept -- a validation-split sweep (same method as `popularity-prior.md`)
  is the natural next step if a stronger weight is worth chasing. The
  Buying/Browsing classifier only looks at the opening message; a session
  that starts vague and firms up a hard constraint on turn 2 stays
  Browsing-routed for its entire conversation, which is a direct, deliberate
  reading of the scenario spec but is itself untested against a "reclassify
  if a constraint firms up later" alternative. Evidence:
  [buying/browsing routing](../reports/experiments/buying-browsing-routing.md).

### T18: Expected-value clarification (rejected, close)

- Date: 2026-08-29
- Origin: `TechJam.docx`'s Layer 4 names this as the explicit next-step
  option: score each attribute by how much it can "statistically eliminate
  the most incorrect products," not yet implemented. The default `candidate`
  policy's `coverage * diversity` heuristic ignores how a covered attribute's
  values are actually *distributed*, and requires >= 2 distinct known values,
  discarding an informative has-it/lacks-it split.
- Hypothesis: scoring by Shannon entropy of each attribute's value
  distribution over the Top-100 pool (with an explicit "unmatched" bucket)
  is a more faithful "expected information gain" and should ask
  better-targeted questions.
- Change: new `_expected_value_order()` in `starter/clarification.py`, added
  as a fourth policy string alongside `fixed`/`profile`/`candidate` -- the
  default (`candidate`) is untouched pending the result.
- New tests: 7, in `tests/test_clarification.py`
  (`ExpectedValuePolicyTest`) — a tie-breaking comparison the coverage
  heuristic cannot resolve, a zero-entropy skip, a has-it/lacks-it split the
  heuristic structurally cannot consider, and an already-asked guard. All
  red-green verified.
- Commands:

  ```powershell
  python -m unittest discover -s tests -v
  python -m scripts.run_clarification_ablation --policies candidate expected_value
  python -m evaluator.local_evaluator
  ```

- Result (full 200-session set): HitRate@10 `0.975` (+1 session over E13),
  MRR `0.670619` (E13: `0.671744`), MTTC `3.060` (E13: `2.930`),
  TechnicalScore `0.847486` (E13: `0.847923`, `-0.000437`).
- Validation-split TechnicalScore (`techjam-clarification-v1`, 80 sessions,
  the project's own decision rule for a clarification-policy choice):
  `candidate` `0.850222` vs `expected_value` `0.848503` — `candidate` wins.
  Development split (120 sessions) narrowly favors `expected_value`
  (`0.846808` vs `0.846391`), so the two splits don't fully agree, but the
  validation split is the one the workflow says to decide on.
- Scenario: buying and browsing HitRate@10 unchanged, but MRR softens
  slightly in both (buying `0.720952 -> 0.705327`, browsing
  `0.665595 -> 0.659345`). Intent Override genuinely improves — one more
  hit, `0.933333 -> 0.966667`, MRR `0.587685 -> 0.611296`. Boundary
  HitRate@10 unchanged; MRR improves (`0.579444 -> 0.661111`) but MTTC
  worsens (`3.6 -> 4.4`).
- Interpretation: not "entropy doesn't work" — it demonstrably helps the
  hardest scenario. With 160 of 200 sessions in Buying+Browsing, a small
  per-session softening there outweighs a real win concentrated in the
  30-session Intent Override scenario, in the aggregate score.
- Decision: **Reject as the default.** Both the pre-registered threshold
  and the project's own validation-split rule point the same direction, so
  there's no ambiguity to resolve in its favor. Genuinely close — a
  `0.0437%` full-set difference, within noise range for this sample size.
- Commit/branch: `review/expected-value-clarification-implementation`
  (implementation and tests preserved, not merged into the default).
- Limitations and next step: route the *clarification policy* the same way
  E13 routes retrieval — use `expected_value` only once an Intent Override
  is detected (mirroring E10's already-tried override-routed pattern, but
  applied at Layer 4 instead of Layer 2), so Buying/Browsing keep
  `candidate` while Intent Override sessions get the policy that measurably
  helps them. Not attempted here, to keep this experiment to one idea.
  Evidence:
  [expected-value clarification](../reports/experiments/expected-value-clarification.md).

### T19: Narrow phrase-independent override (current best)

- Date: 2026-08-30
- Origin: T16's rejected broad attempt ("any new term for an already-known
  non-durable slot is a conflict") regressed one Browsing session
  (`public_0172`): a `feature`-turn's word ("synthetic") lexically matched
  the `material` gazetteer slot, and a later, real `material`-turn's answer
  ("cotton") was misread as overriding it. That report's own next-step
  suggestion -- gate the trigger on `slot == previous ask_attribute` -- was
  checked by hand *before* writing any code and found not to actually fix
  the regression: at the exact moment "cotton" conflicts with "synthetic",
  the agent's own `last_asked` genuinely *was* `"material"`. The problem
  was never which question is being asked *now*; it's where the *existing*
  conflicting value came from *earlier*.
- Hypothesis: track, per slot-term, whether that term was ever recorded in
  a legitimate, on-topic context (opening turn, volunteered unprompted, or
  a direct answer to that slot's own question). Only compare a new term
  against *legitimately-established* existing terms when deciding whether
  to trigger an override; a term that arrived purely as an incidental side
  effect of a different question can never itself become "the thing to
  override."
- Change: `starter/agent.py` gains `self._session_last_asked` (this turn's
  `ask_attribute`, for the next turn to read) and
  `self._session_slot_topic` (per slot-term, a bool: "ever legitimate",
  OR-accumulated across every mention of that term so a later unrelated
  repeat cannot erase earned legitimacy, or vice versa). `_is_intent_override()`
  gains a conflict path that only considers legitimate existing terms.
  `self._session_slots`'s existing shape and everything that reads it
  (the durable/`arrived > OPENING_TURN` survival filter) is untouched --
  purely additive, parallel state.
- New tests: 11, in `tests/test_conversation_state.py`
  (`NarrowPhraseIndependentOverrideTest`) -- the `public_0172`-shaped
  contamination case reproduced in miniature, the recovered
  unprompted-paraphrase capability, and the three safety nets carried over
  from T16's rejected attempt. All red-green verified.
- Commands:

  ```powershell
  python -m unittest discover -s tests -v
  python -m evaluator.local_evaluator
  ```

- Result: **every metric and every scenario is identical to E13** on the
  full 200-session public set. Verified at the session level, not just
  aggregate: comparing `sessions[]` against E13's stored evidence JSON
  gives 0 differing sessions out of 200.
- Initial decision (later corrected on review): recorded here as "Keep, new
  current best" on the reasoning that it closes a real, twice-documented
  private-set risk (the literal-phrase dependency) at zero measured public
  cost.
- **Correction after review:** this is not an improvement on any
  measurable metric -- 0/200 public sessions differ from E13, full stop.
  The entire claimed value rests on an *unverifiable* assumption: that the
  private set's 800 sessions phrase a change of mind differently than the
  public simulator's one fixed sentence. There is no way to confirm this
  from here (the private evaluator is not available), and if the private
  set generates override messages the same way, this change does nothing
  at all, ever, while still adding real state (`_session_last_asked`,
  `_session_slot_topic`) and logic to maintain. Calling this a "clean win"
  during initial reporting overstated it -- it is a judgment call about
  risk tolerance with a real complexity cost and an unproven benefit, not
  evidence of being better. **Reverted** at the project owner's direction;
  `main` is back to E13 byte-for-byte
  (`starter/agent.py`, `tests/test_conversation_state.py` checked out from
  E13's commit `92d4714`).
- Commit/branch: implementation preserved on
  `review/narrow-phrase-independent-override-implementation` (renamed from
  `experiment/narrow-phrase-independent-override`), not merged into `main`,
  not pushed to the shared remote.
- Limitations and next step: this is still narrower than "any conflict,
  anywhere" -- a slot's first legitimate value can only be established on
  the opening turn, when volunteered unprompted, or when directly asked
  about. A genuine change of mind about something the customer stated
  purely as contamination (never legitimately, on its own terms) still
  cannot be detected. Whether to revisit this at all should wait for actual
  evidence about private-set override phrasing, not another guess. Evidence:
  [narrow phrase-independent override](../reports/experiments/narrow-phrase-independent-override.md).

### T20: Dense retrieval, standalone (rejected; feeds E17)

- Date: 2026-08-30
- Origin: `TechJam.docx` Layer 1 lists Dense Retrieval, never attempted --
  retrieval has always been lexical BM25. A full transformer embedding
  model is feasible (network access works) but risks real per-turn latency
  at scale; Latent Semantic Analysis (TF-IDF + Truncated SVD) is inference-
  only after one startup fit, needs no downloaded weights, and is a real,
  if older and weaker, dense-embedding technique.
- Prediction recorded *before* running anything: this project's own
  `slot-memory-and-retrieval-ablation.md` documents that the practice
  simulator's disclosed constraints are sliced verbatim from the target's
  own catalog metadata -- there is no organic paraphrasing in the public
  set for a semantic method to bridge, so little to no gain was expected
  here specifically.
- Change: new `starter/dense.py::DenseIndex`. New `Agent(retrieval_mode=...)`
  constructor argument; `"dense"` replaces BM25 candidate retrieval
  entirely for this isolated test (not a proposed final design). Default
  (`"bm25"`) is unchanged, confirmed by a dedicated regression test.
- New tests: 14 (`tests/test_dense.py`, plus 2 agent-integration tests).
  93/93 project tests pass. New `scripts/run_retrieval_mode.py`.
- New dependency: `scikit-learn` (+ `scipy`, `joblib`, `threadpoolctl`).
  First non-stdlib dependency this project has introduced.
- Commands:

  ```powershell
  python -m unittest discover -s tests -v
  python -m scripts.run_retrieval_mode --retrieval-mode dense --output reports/experiments/dense-retrieval.json
  ```

- Result: HitRate@10 `0.665`, MRR `0.534054`, MTTC `5.625`, TechnicalScore
  `0.600216` (E13: `0.847923`). Matches the prediction: much weaker overall,
  as expected, since this strips out E1/E11/E13's accumulated reranking,
  popularity, and routing machinery to isolate retrieval quality alone.
- **The actual finding:** session-by-session against E13 -- dense recovers
  2 of E13's 6 public misses (`public_0052`, `public_0179`) that BM25 never
  reaches at all, while losing 63 sessions BM25 gets right. Not strictly
  worse everywhere: genuine complementary recall, exactly the signal RRF
  fusion is designed to combine.
- Startup cost: ~26s one-time `TruncatedSVD` fit (not per-turn), full
  200-session eval ~32s after that.
- Decision: **Reject as a standalone mode.** Proceed directly to E17 (RRF
  fusion) using this experiment's dense index and complementarity evidence
  -- this experiment's purpose was exactly to produce that evidence before
  attempting fusion.
- Commit/branch: local commit on `experiment/dense-retrieval`, not pushed.
- Limitations and next step: `n_components` and `max_features` are
  reasoned defaults, not swept. Evidence:
  [dense retrieval](../reports/experiments/dense-retrieval.md).

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
  | **Total** | **53** | Current full regression suite |

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
