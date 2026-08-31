  # Experiment History and Method Comparison Matrix

  This file is the project's experiment ledger. Every change to retrieval,
  ranking, conversation state, or question policy must add a result here,
  including failed experiments. It should answer three questions directly:

  1. Where did the project start?
  2. What changed in each experiment?
  3. Which method is best, and why was each method kept or rejected?

> Current best: E32 Category field weight, at public HitRate@10 `0.995`, MRR
> `0.823353`, MTTC `2.355`, and TechnicalScore `0.917406`. It corrects a
> reliability ordering rather than adding a signal: the simulator quotes the
> target's category path into the opening message, so `categories` is the one
> field guaranteed to overlap the query, yet it had been weighted below
> `title` since E1. Unlike E21, its gain **grows** under the coverage-stress
> diagnostic (`+0.011213` official, `+0.021101` stressed) and recovers three
> stressed sessions of HitRate@10. See E32.
>
> Previous best: the merged line, at public HitRate@10 `0.995`, MRR `0.791810`,
> MTTC `2.405`, and TechnicalScore `0.906943`. See E28, T36, T37, T38 and T39.
>
> Two lines were developed in parallel and merged twice, on 2026-08-30.
> E12-E23 came from `feat/hs` and improved rank quality; E24-E27 came from
> `experiment/constraint-ledger` and improved conversational coverage. Neither
> knew about the other, so E24-E27 are numbered by merge order rather than by
> date, and their `Delta` values are within-line against E11 rather than
> against the row above them. See the `Baseline` column.
>
> Current best: E22 Constraint Satisfaction on All Routes, with public
> HitRate@10 `0.980`, MRR `0.770470`, MTTC `2.820`, and TechnicalScore
> `0.884741`. Unlike E21 it also gains under the coverage-stress diagnostic
> (`+0.005588`), because it is a statement about the conversation rather
> than about catalog metadata.
>
> E21 was developed on `feat/hs` in parallel with E13-E20 and merged after
> E20, so it is numbered after the branch it merged into rather than by the
> date it was run. It stacks on E19 without moving HitRate@10 or any
> scenario hit rate: the entire `+0.012194` is rank quality (MRR
> `+0.040980`), which is what a tie-breaking prior is expected to buy.
>
> **E21, still a retained layer, carries a documented transfer risk.** Under T25's coverage-stress
> diagnostic its gain reverses: `+0.012194` on the official catalog,
> `-0.020274` when target price coverage is cut to the catalog-wide rate.
> No other retained layer reverses. Official metrics still select methods,
> so E21 stands, but read T26 before relying on its margin.
>
> E19 Phrase (Bigram) Bonus remains the largest single-experiment gain
> since E13: 2 sessions recovered, 0 lost, versus E18.
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
  catalog, and the unmodified official evaluator.

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
| E13 | Buying/Browsing routing | Classify route at turn 1; reward candidates matching every known constraint, Buying sessions only | 79 | **0.970** | +0.005 | **0.671744** | **2.930** | **0.8070** | **0.847923** | **+0.006085** | Superseded by E18 | `92d4714` |
| E14 | Expected-value clarification | Score each attribute by Shannon entropy of its value split, not coverage*diversity | 86 | 0.975 | +0.005 | 0.670619 | 3.060 | 0.7940 | 0.847486 | -0.000437 | Reject (close; validation split agrees) | Review branch |
| E15 | Narrow phrase-independent override | Override trigger only on a conflict with a slot value legitimately established for its own question | 90 | 0.970 | +0.000 | 0.671744 | 2.930 | 0.8070 | 0.847923 | +0.000000 | Reverted on review -- see note above matrix | `review/narrow-phrase-independent-override-implementation` |
| E16 | Dense retrieval (standalone) | TF-IDF + Truncated SVD replaces BM25 entirely, isolated comparison | 93 | 0.665 | -0.305 | 0.534054 | 5.625 | 0.5375 | 0.600216 | -0.247707 | Reject as standalone; feeds E17 | Review branch |
| E17 | RRF hybrid retrieval | Fuse BM25 + dense top-100 by Reciprocal Rank Fusion, truncate to 100 | 107 | 0.945 | -0.025 | 0.665696 | 3.065 | 0.7935 | 0.830909 | -0.017014 | Reject (traced: pool truncation evicts good candidates) | Review branch |
| E18 | Semantic reranking score | Add dense cosine-similarity term to reranker (bi-encoder-style, weight 1.0) | 109 | **0.970** | +0.000 | **0.677607** | **2.920** | **0.8080** | **0.849882** | **+0.001959** | Superseded by E19 | `b3e88b8` |
| E19 | Phrase (bigram) bonus | Reward candidates matching the customer's adjacent word-pairs as a literal substring | 115 | **0.980** | +0.010 | **0.715919** | **2.815** | **0.8185** | **0.868476** | **+0.018594** | Superseded by E21 | `e9dc276` |
| E20 | Query-side stemming | Add each query term's singular form as an extra OR-term (FTS5 tokenizer does no stemming) | 126 | 0.930 | -0.050 | 0.666079 | 3.170 | 0.7830 | 0.821424 | -0.047052 | Reject (traced: broadens fixed-100 retrieval cutoff) | Review branch |
| E21 | Price presence prior | Add a flat `2.0` bonus for carrying a price at all; developed on `feat/hs`, merged after E20 | 143 | **0.980** | +0.000 | **0.756899** | 2.820 | 0.8180 | **0.880670** | **+0.012194** | Superseded by E22 | `fe86b63` |
| E22 | Constraint satisfaction on all routes | Apply E13's completeness bonus to Browsing sessions too, at the unchanged `4.0` | 158 | **0.980** | +0.000 | **0.770470** | 2.820 | 0.8180 | **0.884741** | **+0.004071** | **Current best** | `feat/hs` |
| E23 | Turn-recency term weighting | Scale each query term by `1 + w * (arrival_turn - 1)` | 158 | 0.980 | +0.000 | 0.754359 | 2.820 | 0.8180 | 0.879908 | -0.000762 | Reject (monotonic decline, no peak) | `feat/hs` |
  `Δ` is measured against whatever the `Baseline` column names, which is the
  previous retained method for every row except E22-E27. Those were developed
  in parallel on another branch and measured against E11, so their deltas do
  **not** telescope with the rows above them and the column cannot be summed
  down the table.

  `Δ` is also a historical fact rather than a current one: it records what a
  method bought on the system as it stood that day. For what each retained
  mechanism is worth in the system as it stands **now**, see the
  [merged-system ablation](../reports/experiments/merged-system-ablation.md),
  whose marginal contributions are comparable across every row because all of
  them are measured against the same system. Two mechanisms measure near zero
  there.

| ID | Method | Main change | Automated tests | Baseline | HitRate@10 | Δ HitRate | MRR | MTTC ↓ | Efficiency | TechnicalScore | Δ Score | Decision | Commit |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| E0 | Weak BM25 baseline | Return BM25 Top-10 directly; no state or questions | 3 | — | 0.125 | Reference | 0.068034 | 9.810 | 0.1190 | 0.106710 | Reference | Baseline | `3407835` |
| E1 | Field reranker v1 | Rerank BM25 Top-100 by field coverage | 10 | prev. retained | 0.160 | +0.035 | 0.076750 | 9.460 | 0.1540 | 0.133825 | +0.027115 | **Keep** | `db65ad2` |
| E1-A | Reranker + BM25 rank prior | Add the original BM25 rank as a bonus to E1 | Targeted | prev. retained | 0.155 | -0.005 | 0.073992 | 9.510 | 0.1490 | 0.129498 | -0.004327 | Reject | Not committed |
| E2 | Conversation State v1 | Accumulate constraints, handle overrides, ask profile-guided non-repeating questions | 14 | prev. retained | 0.870 | +0.710 | 0.533748 | 4.565 | 0.6435 | 0.723824 | +0.589999 | Keep | `d770b6f` |
| E3-A | Fixed clarification | Use a fixed attribute question order | 21 | prev. retained | 0.865 | -0.005 | 0.523492 | 4.640 | 0.6360 | 0.716748 | -0.007076 | Reject | `fa84de2` |
| E3-B | Profile clarification | Use the E2 profile-first policy as the ablation baseline | 21 | prev. retained | 0.870 | +0.000 | 0.533748 | 4.565 | 0.6435 | 0.723824 | +0.000000 | Previous baseline | `fa84de2` |
| E3-C | Candidate-aware clarification | Ask first about a covered, varied attribute in the Top-100 candidates | 21 | prev. retained | **0.870** | **+0.000** | **0.544236** | **4.410** | **0.6590** | **0.730071** | **+0.006247** | Superseded by E9 | `fa84de2` |
| E4-A | Balanced clarification | Prioritize the intersection of profile preferences and current product differences | 23 during experiment | prev. retained | 0.870 | +0.000 | 0.536248 | 4.540 | 0.6460 | 0.725074 | -0.004997 | Reject | Review branch only |
| E4-B | Always-ask-other probe | Always ask `other`; diagnostic only | 35 | prev. retained | 0.840 | -0.030 | 0.522508 | 3.635 | 0.7365 | 0.724052 | -0.006019 | Reject (diagnostic) | Not separately committed |
| E5 | Slot-aware override memory | Preserve category/department slots during override; clear the rest | 41 | prev. retained | **0.875** | +0.005 | 0.540300 | **4.290** | 0.6710 | **0.733790** | +0.003719 | Keep (weak evidence) | Included in remote series |
| E6 | Turn-aware override memory | Also preserve constraints learned from turn 2 onward | 48 | prev. retained | 0.875 | +0.000 | 0.540300 | 4.290 | 0.6710 | 0.733790 | +0.000000 | Reject (no effect) | Included in remote series |
| E7 | Candidate pool 100 -> 500 | Increase only the BM25 candidate pool | 51 | prev. retained | 0.875 | +0.000 | 0.528762 | 4.190 | 0.6810 | 0.732329 | -0.001461 | Reject | Included in remote series |
| E8-A | Pool-frequency IDF (incorrect) | Treat candidate-pool term frequency as IDF | 53 | prev. retained | 0.790 | -0.085 | 0.459067 | 4.975 | 0.6025 | 0.653220 | -0.080570 | Reject (reasoning error) | Included in remote series |
| E8-B | Catalog IDF + pool 500 | Weight with catalog-wide `fts5vocab` document frequency | 54 during experiment | prev. retained | 0.845 | -0.030 | 0.522619 | 4.625 | 0.6375 | 0.706786 | -0.027004 | Reject | Included in remote series |
| E8-C | Catalog IDF + pool 100 | Same catalog IDF with the candidate pool kept at 100 | 54 during experiment | prev. retained | 0.860 | -0.015 | 0.540980 | 4.640 | 0.6360 | 0.719494 | -0.014296 | Reject | Included in remote series |
| E9 | Slot conflict resolution | Give each gazetteer term one slot; pool 100 and no IDF | 53 | prev. retained | **0.895** | +0.020 | **0.549056** | **4.215** | 0.6785 | **0.747917** | **+0.014127** | Superseded by E11 | `c1941f6` merge series |
| E10 | Override-routed IDF | If intent-override detected, then route to use IDF over the whole catalogue | 56 | prev. retained | 0.890 | -0.005 | 0.551708 | 4.270 | 0.6730 | 0.745112 | -0.002805 | REJECTED | Included in remote series|
| E11 | Popularity prior | Add `1.2 * log1p(rating_number)` to the rerank score | 58 | prev. retained | **0.965** | +0.070 | **0.662125** | **2.965** | **0.8035** | **0.841838** | **+0.093921** | Superseded by E13 | `52789c4` |
| E12 | Phrase-independent override | Trigger override on a same-slot value conflict, not only the literal simulator sentence | 77 | prev. retained | 0.960 | -0.005 | 0.661292 | 3.005 | 0.7995 | 0.838288 | -0.003550 | Reject (design tradeoff, see report) | Review branch |
| E13 | Buying/Browsing routing | Classify route at turn 1; reward candidates matching every known constraint, Buying sessions only | 79 | prev. retained | **0.970** | +0.005 | **0.671744** | **2.930** | **0.8070** | **0.847923** | **+0.006085** | Superseded by E18 | `92d4714` |
| E14 | Expected-value clarification | Score each attribute by Shannon entropy of its value split, not coverage*diversity | 86 | prev. retained | 0.975 | +0.005 | 0.670619 | 3.060 | 0.7940 | 0.847486 | -0.000437 | Reject (close; validation split agrees) | Review branch |
| E15 | Narrow phrase-independent override | Override trigger only on a conflict with a slot value legitimately established for its own question | 90 | prev. retained | 0.970 | +0.000 | 0.671744 | 2.930 | 0.8070 | 0.847923 | +0.000000 | Reverted on review -- see note above matrix | `review/narrow-phrase-independent-override-implementation` |
| E16 | Dense retrieval (standalone) | TF-IDF + Truncated SVD replaces BM25 entirely, isolated comparison | 93 | prev. retained | 0.665 | -0.305 | 0.534054 | 5.625 | 0.5375 | 0.600216 | -0.247707 | Reject as standalone; feeds E17 | Review branch |
| E17 | RRF hybrid retrieval | Fuse BM25 + dense top-100 by Reciprocal Rank Fusion, truncate to 100 | 107 | prev. retained | 0.945 | -0.025 | 0.665696 | 3.065 | 0.7935 | 0.830909 | -0.017014 | Reject (traced: pool truncation evicts good candidates) | Review branch |
| E18 | Semantic reranking score | Add dense cosine-similarity term to reranker (bi-encoder-style, weight 1.0) | 109 | prev. retained | **0.970** | +0.000 | **0.677607** | **2.920** | **0.8080** | **0.849882** | **+0.001959** | Superseded by E19 | `b3e88b8` |
| E19 | Phrase (bigram) bonus | Reward candidates matching the customer's adjacent word-pairs as a literal substring | 115 | prev. retained | **0.980** | +0.010 | **0.715919** | **2.815** | **0.8185** | **0.868476** | **+0.018594** | Superseded by E21 | `e9dc276` |
| E20 | Query-side stemming | Add each query term's singular form as an extra OR-term (FTS5 tokenizer does no stemming) | 126 | prev. retained | 0.930 | -0.050 | 0.666079 | 3.170 | 0.7830 | 0.821424 | -0.047052 | Reject (traced: broadens fixed-100 retrieval cutoff) | Review branch |
| E21 | Price presence prior | Add a flat `2.0` bonus for carrying a price at all; developed on `feat/hs`, merged after E20 | 143 | prev. retained | **0.980** | +0.000 | **0.756899** | 2.820 | 0.8180 | **0.880670** | **+0.012194** | **Current best** | `fe86b63` |
| E24-A | Constraint ledger Stage 0 | Three override-state correctness fixes, measured separately | 103 | E11 (parallel) | 0.965 | +0.000 | 0.662125 | 2.965 | 0.8035 | 0.841838 | +0.000000 | Reject 2 of 3; slot negation guard retained on correctness | Not committed |
| E24-B | Constraint ledger Stage 1 | Append-only entries with status instead of deletion; query projected from active entries | 118 | E11 (parallel) | **0.975** | +0.010 | **0.677881** | **2.810** | 0.8190 | **0.854664** | **+0.012826** | Keep | See branch |
| E24-C1 | Ledger term weighting | Scale answered constraints against volunteered ones in the reranker | 127 | E11 (parallel) | 0.970 | -0.005 | 0.676315 | 2.865 | 0.8135 | 0.850594 | -0.004070 | Reject; validation peaks at the off position | Not committed |
| E24-C | Information-gain probe | Ask an open question after a turn that adds no ledger entry | 127 | E11 (parallel) | **0.980** | +0.005 | **0.698381** | **2.540** | **0.8460** | **0.868714** | **+0.014050** | **Current best** | See branch |
| E25-A | Catalog quality prior | Add `quality_weight * average_rating` to the rerank score | 127 | E11 (parallel) | 0.980 | +0.000 | 0.704938 | 2.540 | 0.8460 | 0.870681 | +0.001967 full, -0.000052 validation | Reject; development and validation argmax disagree | Not committed |
| E25-B | Exhaustion-triggered catalog IDF | Apply catalog IDF to rerank weights once the information-gain counter fires | 127 | E11 (parallel) | 0.980 | +0.000 | 0.698381 | 2.540 | 0.8460 | 0.868714 | +0.000000 | Reject; zero sessions changed at any threshold | Not committed |
| E26 | Implicit-rejection reranking | Penalise already-shown candidates once the conversation is stuck; keep asking instead of assuming exhaustion | 133 | E11 (parallel) | **0.995** | +0.015 | 0.694964 | **2.465** | 0.8535 | **0.876689** | **+0.007975** | Retired at T38 (marginal `0.000083`) | See branch |
| E27 | Stuck-path clarification policy | Route the persistently-stuck branch through `select_attribute` instead of round-robin | 137 | E11 (parallel) | 0.995 | +0.000 | 0.694964 | 2.465 | 0.8535 | 0.876689 | +0.000000 | Reject; identical score, degenerate behaviour | Not committed |
| E28 | Merged line | E12-E23 rank quality merged with E24-E27 conversational coverage; merged twice, see T36 and T39 | 195 | E22 | **0.995** | +0.015 | **0.791810** | 2.405 | 0.8595 | **0.906943** | **+0.022202** | **Current best** | See T39 |
| E29 | Slot-projected semantic query | Build the dense index's query from active slotted ledger entries instead of the raw term bag | 197 | E28 | 0.995 | +0.000 | 0.791976 | 2.405 | 0.8595 | 0.906993 | +0.000050 | Reject; 2.7% of a 0.001871 budget | Not committed |
| E30 | Hard/soft constraint separation | Require only constraints the customer phrased as requirements, detected from the evaluator's wording | 197 | E28 | 0.995 | +0.000 | 0.784006 | 2.405 | 0.8595 | 0.904602 | -0.002341 | Reject; loosens a bonus whose value is strictness | Not committed |
| E30-A | Separate hard-constraint bonus | Keep `required_terms` and add a second completeness test over the hard subset | 197 | E28 | 0.995 | +0.000 | 0.791810 | 2.405 | 0.8595 | 0.906943 | +0.000000 | Reject; satisfied by 0.1 candidates of 100 | Not committed |
| E31 | Route-conditional weights | Per-route semantic/popularity weights keyed by `_classify_route`; the first live consumer of the route since E22 | 204 | E28 | 0.990 | -0.005 | 0.782216 | 2.445 | 0.8555 | 0.900765 | -0.005428 | Reject (validation gain reverses on the full set) | Report merged; code on `experiment/route-conditional-weights` |
| E32 | Category field weight | `FIELD_WEIGHTS["categories"]` 3.0 -> 6.0; the first field-weight sweep in the project; gain grows under coverage stress | 205 | E28 | **0.995** | +0.000 | **0.823353** | **2.355** | **0.8645** | **0.917406** | **+0.011213** | **Current best** | `experiment/ngram-phrase-bonus` |
| E32-A | N-gram phrase bonus | Extend E19 bigrams to runs of 3+, phrase credit scaled by run length | 205 | E28 | 0.995 | +0.000 | 0.797464 | 2.405 | 0.8595 | 0.908639 | +0.002446 | Reject (negative in combination with E32) | Same branch, `phrase_max_n` |
| E33 | Union-hybrid retrieval | Append dense hits after the BM25 pool instead of E17's fuse-and-truncate; plus a query-side paraphrase stress diagnostic | 214 | E32 | 0.995 | +0.000 | 0.800665 | 2.245 | 0.8755 | 0.912799 | -0.004607 | Reject (costs 0.004607, buys 0.001840 under the worst stress) | `experiment/ngram-phrase-bonus` |

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
| E17 RRF hybrid retrieval | 0.9375 | 0.9750 | 0.900000 | 0.9000 |
| E18 Semantic reranking score | **0.9625** | **1.0000** | **0.933333** | 0.9000 |
| E19 Phrase (bigram) bonus | **0.9875** | **1.0000** | **0.933333** | 0.9000 |
| E20 Query-side stemming | 0.9375 | 0.9500 | 0.866667 | 0.9000 |
| E21 Price presence prior | **0.9875** | **1.0000** | **0.933333** | 0.9000 |
| E22 Constraint satisfaction, all routes | **0.9875** | **1.0000** | **0.933333** | 0.9000 |
| E23 Turn-recency weighting | **0.9875** | **1.0000** | **0.933333** | 0.9000 |
| E24-A Stage 0 retained | 0.9500 | **1.0000** | 0.933333 | 0.9000 |
| E24-B Constraint ledger | 0.9500 | **1.0000** | **1.000000** | 0.9000 |
| E24-C Information-gain probe | 0.9500 | **1.0000** | **1.000000** | **1.0000** |
| E26 Implicit-rejection reranking | **0.9875** | **1.0000** | **1.000000** | **1.0000** |
| E28 Merged line | **0.9875** | **1.0000** | **1.000000** | **1.0000** |
| E32 Category field weight | **0.9875** | **1.0000** | **1.000000** | **1.0000** |

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
- Commit/branch: `92d4714`, merged to `main` and pushed to the shared
  remote.
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
- Commit/branch: `review/dense-retrieval-implementation` (local only, not
  pushed).
- Limitations and next step: `n_components` and `max_features` are
  reasoned defaults, not swept. Evidence:
  [dense retrieval](../reports/experiments/dense-retrieval.md).

### T21: RRF hybrid retrieval (rejected; mechanism traced)

- Date: 2026-08-30
- Origin: `TechJam.docx` Layer 1's third option -- fuse BM25's and dense's
  leaderboards by Reciprocal Rank Fusion rather than replacing one with the
  other. T20 found real, if narrow, complementary signal (2 unique dense
  hits) motivating a genuine attempt at fusion.
- Change: new `starter/fusion.py::reciprocal_rank_fusion` (standard RRF,
  `k=60`). `Agent(retrieval_mode="rrf")` fetches BM25's and dense's top-100
  independently, fuses, and truncates to the top 100 by fused rank -- that
  set feeds the existing reranker unchanged. `bm25` mode internals
  refactored into a shared `_bm25_rank()` helper, confirmed byte-identical
  by regression test.
- New tests: 8 (6 in `tests/test_fusion.py`, 2 agent-integration). One
  test's own premise was wrong on inspection -- RRF's convex scoring means
  extreme ranks {1,3} score marginally higher than middling ranks {2,2}, a
  real property, not a bug -- corrected before trusting it. 107/107 project
  tests pass.
- Commands:

  ```powershell
  python -m unittest discover -s tests -v
  python -m scripts.run_retrieval_mode --retrieval-mode rrf --output reports/experiments/rrf-hybrid-retrieval.json
  ```

- Result: HitRate@10 `0.945`, MRR `0.665696`, MTTC `3.065`, TechnicalScore
  `0.830909` (E13: `0.847923`, `-0.017014`). Session-by-session: 1 recovered
  (`public_0071`), 6 lost. Net -5.
- **Root cause, traced precisely** on `public_0040` (an E13 rank-1 hit):
  the target enters BM25's own top-100 at turn 6, but only at rank 72 --
  not in dense's top-100 at all. E13's reranker evidently promotes a
  mediocre-BM25-rank-but-correct candidate very effectively once it's in
  the pool (rank 72 -> rank 1, via field weighting + completeness bonus +
  popularity). Under RRF, the candidate *pool itself* is truncated to 100
  by fused rank *before* the reranker runs: other products' joint
  BM25+dense agreement pushes the target's fused rank outside the top 100
  entirely, so the reranker never sees it. Not a reranking failure --
  retrieval discarding a correct candidate to make room for one whose only
  qualification is agreement between two lists, one of which (dense, E16:
  TechnicalScore `0.600` standalone) is meaningfully noisier here.
- Decision: **Reject.** Confirms E16's own predicted risk exactly: fusing a
  much weaker signal into a much stronger one can demote good candidates as
  easily as promote missed ones. Net here: 6 lost for 1 recovered.
- Commit/branch: `review/rrf-hybrid-retrieval-implementation` (local only,
  not pushed).
- Limitations and next step: take the **union** of both top-100 lists
  (padding, not truncating) instead of truncating the fused ranking, so
  dense can only ever add candidates BM25's own net missed, never displace
  ones it already caught. Not attempted here, to test standard RRF as the
  doc describes it first. Evidence:
  [rrf hybrid retrieval](../reports/experiments/rrf-hybrid-retrieval.md).

### T22: Semantic reranking score (current best)

- Date: 2026-08-30
- Origin: `TechJam.docx` Layer 2's Cross-Encoder Reranker option. A true
  cross-encoder needs a transformer doing cross-attention between query and
  candidate -- real per-turn latency risk at this project's scale (up to
  100 candidates x 10 turns x 200 sessions). Tests the doc's *intent*
  (semantic relevance beyond keyword-field-weight sums) using E16's
  already-built, already-fast LSA vectors as a bi-encoder-style proxy --
  explicitly disclosed as not a true cross-encoder.
- Hypothesis: unlike E16/E17, this only adds a scoring term over the *same*
  unchanged BM25 candidate set -- lower risk of E17's pool-eviction failure
  mode, since retrieval itself doesn't change.
- Change: `DenseIndex` gains `project()`/`vector_for()`. `rerank_candidates`
  gains `semantic_scores`/`semantic_weight` (same pattern as
  `popularity_weight`). `Agent` computes cosine similarity between the
  query and each already-retrieved BM25 candidate, passed to the reranker.
  New `SEMANTIC_WEIGHT = 1.0` default.
- **Bug found and fixed mid-implementation:** defaulting `semantic_weight`
  to nonzero meant the dense index now builds by default, and it crashed
  (`ValueError: empty vocabulary`) on the empty-catalog fixture several
  existing tests use to isolate conversation-state logic. Fixed with the
  same principle `_load_gazetteer` uses: degrade to a no-op on a degenerate
  input rather than fail the scored path. Caught by running the full test
  suite before declaring green, not assumed.
- New tests: 9 (4 `test_dense.py`, 3 `test_reranker.py`, 2 agent-integration).
  One pre-existing test's name was corrected -- it claimed the default was
  "unaffected," which stopped being true once the default weight changed;
  rewritten to explicitly test `semantic_weight=0.0` opting back out.
  109/109 project tests pass.
- Commands:

  ```powershell
  python -m unittest discover -s tests -v
  python -m scripts.run_retrieval_mode --semantic-weight 1.0 --output reports/experiments/semantic-reranking.json
  python -m evaluator.local_evaluator   # confirms the plain default matches
  ```

- Triangulated three weights (not a full sweep): `0.5` -> TechnicalScore
  `0.849534`; `1.0` -> `0.849882` (best); `2.0` -> `0.845118` (worse than
  E13). Chose `1.0`.
- Result: HitRate@10 `0.970` (unchanged), MRR `0.671744 -> 0.677607`, MTTC
  `2.930 -> 2.920`, TechnicalScore `0.847923 -> 0.849882` (`+0.001959`).
  **Zero sessions change hit/miss status** in either direction -- among the
  194 already-correct sessions, 9 rank higher and 4 rank slightly lower.
  Purely a ranking-quality effect, not a recall effect.
- At weight `2.0`, the same failure mode E17 hit with RRF (demoting
  genuinely correct candidates) reappears, just at the reranking stage
  instead of retrieval -- consistent evidence that this project's dense/LSA
  signal is real but must stay a *light* supplementary term.
- Decision: **Keep. New current best.** `SEMANTIC_WEIGHT = 1.0` is now the
  `Agent` default, confirmed with the plain, unmodified `Agent()`
  construction.
- Commit/branch: `b3e88b8`, merged to `main` and pushed to the shared
  remote.
- Limitations and next step: a full validation-split sweep (same method as
  `popularity-prior.md`) could find a better weight than this 3-point
  triangulation did. Evidence:
  [semantic reranking](../reports/experiments/semantic-reranking.md).

### T23: Phrase (bigram) bonus (current best)

- Date: 2026-08-30
- Origin: researched separately -- `TechJam.docx`'s remaining Layer 1/2
  options are now all tried (E16/E17/E18). Classic, well-established IR
  technique: E1's field-weighted reranker scores every query word
  independently, so "running" and "shoe" scattered apart in a document
  score identically to "running shoe" as an adjacent phrase.
- Hypothesis: rewarding candidates whose text contains the customer's
  adjacent word-pairs as a literal substring should improve precision.
  Unlike E16/E17, this only adds a scoring term over the unchanged BM25
  pool (same lower-risk shape as E18).
- Change: new `starter/reranker.py::extract_bigrams` and
  `phrase_terms`/`phrase_weight` on `rerank_candidates`. `starter/agent.py`
  computes bigrams from the current turn's raw message each turn.
- **Bug found and fixed, unrelated to this experiment's own logic:**
  `scripts/run_retrieval_mode.py`'s `--semantic-weight` had a hardcoded
  default of `0.0`, silently overriding `Agent`'s real default (`1.0`
  since E18) whenever invoked without that flag -- stale since E18 changed
  the default and the script wasn't updated. Fixed by defaulting both
  `--semantic-weight` and the new `--phrase-weight` to `None`, meaning
  "use `Agent`'s own default," so this class of staleness can't recur.
- New tests: 10 (`ExtractBigramsTest`, `PhraseBonusTest`). 115/115 project
  tests pass.
- Commands:

  ```powershell
  python -m unittest discover -s tests -v
  python -m scripts.run_retrieval_mode --phrase-weight 1.0 --output reports/experiments/phrase-bonus.json
  python -m evaluator.local_evaluator   # confirms the plain default matches
  ```

- Triangulated three weights on top of E18's `semantic_weight=1.0`: `0.5`
  -> TechnicalScore `0.855221`; `1.0` -> `0.868476` (best); `2.0` ->
  `0.866975` (past the peak). Chose `1.0`.
- Result: HitRate@10 `0.970 -> 0.980`, MRR `0.677607 -> 0.715919`, MTTC
  `2.920 -> 2.815`, TechnicalScore `0.849882 -> 0.868476` (`+0.018594`) --
  the largest single-experiment gain since E13. **2 sessions recovered**
  (`public_0161`, `public_0179`), **0 lost**.
- Decision: **Keep. New current best.** `PHRASE_WEIGHT = 1.0` is now the
  `Agent` default, confirmed with the plain, unmodified `Agent()`
  construction. The size of this gain suggests bag-of-words scoring really
  was leaving precision on the table for phrase-shaped constraints, not a
  dataset-specific quirk.
- Commit/branch: `e9dc276`, merged to `main` and pushed to the shared
  remote.
- Limitations and next step: a full validation-split sweep could find a
  better weight than this 3-point triangulation. Evidence:
  [phrase bonus](../reports/experiments/phrase-bonus.md).

### T24: Query-side stemming (rejected, mechanism traced -- 5th of 5 requested experiments)

- Date: 2026-08-30
- Origin: researched separately. `analysis/gazetteer.py::normalize_term`
  already singularizes matched vocabulary terms, but only on the gazetteer
  slot-extraction path. FTS5's `unicode61` tokenizer does no stemming on
  either the index or query side, so a customer saying "shoes" cannot
  match a catalog title that only says "shoe."
- Hypothesis (recorded before implementation, and the part that turned out
  wrong): adding each query term's singular form as an *extra* OR-term is
  "a pure superset expansion... essentially risk-free," since no existing
  term is ever removed.
- Change: new `starter/stemming.py::expand_with_stems`, reusing
  `normalize_term`. Applied to the FTS5 match expression and the
  reranker's query terms; not to the stored accumulated term list.
- New tests: 5 (4 `test_stemming.py`, 1 agent-integration). 126/126
  project tests pass before the evaluator run.
- Commands:

  ```powershell
  python -m unittest discover -s tests -v
  python -m evaluator.local_evaluator
  ```

- Result: HitRate@10 `0.980 -> 0.930`, MRR `0.677607 -> 0.666079`
  (comparison MRR shown against E19), MTTC `2.815 -> 3.170`, TechnicalScore
  `0.868476 -> 0.821424` (`-0.047052`). Session-by-session: 2 recovered, 12
  lost. Net -10.
- **Root cause, traced precisely on `public_0028`:** without stemming, the
  target sits at BM25 rank 95 of 100 from turn 3 onward -- barely inside
  the pool. With stemming, the query gains `case`/`organizer`/`wallet`/
  `matter` as extra terms; the target falls out of the top 100 entirely.
  **The "risk-free superset" hypothesis was wrong**: retrieval is
  `... MATCH ? ORDER BY bm25(...) LIMIT 100`, a fixed-size window, not an
  unbounded list. Adding OR-terms doesn't just add ways for the true
  target to match -- it makes *more of the other 50,000 products* qualify
  and compete for the same 100 slots. A term is only actually risk-free to
  add if it doesn't change who else qualifies, which query expansion does
  not guarantee. This is the same fundamental failure mode E17 found with
  RRF fusion (a borderline-but-correct candidate evicted before the
  reranker runs), reached here by a completely different mechanism
  (broadening one query's match criteria, not merging two ranked lists).
- Decision: **Reject.** Confirms, via a second independent mechanism, the
  same lesson E17 already taught: this project's fixed-size retrieval
  cutoff is more fragile to *any* recall-broadening change than it first
  appears.
- Commit/branch: `review/query-stemming-implementation` (implementation
  and tests preserved, not merged into the default).
- Limitations and next step: a version that only expands terms *within* an
  already-retrieved candidate's scoring (matching E18/E19's shape --
  reranking-only, not retrieval-broadening) would avoid this exact failure
  mode; not attempted here, to test the direct approach first. Evidence:
  [query-side stemming](../reports/experiments/query-stemming.md).

### T25: Coverage-stress dual evaluation (diagnostic environment)

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

**Re-run against E19 (the current best as of this merge)**, using this same
tool unmodified (`python -m scripts.run_dual_catalog_evaluation`): official
HitRate@10 `0.980`, MRR `0.715919`, TechnicalScore `0.868476`; coverage-stress
HitRate@10 `0.980` (**0/200 sessions change hit/miss status, in any
scenario**), MRR `0.730494`, TechnicalScore `0.873848` (`+0.005372`). Same
pattern as the original E11 run: a small positive delta, no scenario
regresses. E13/E18/E19's added layers do not introduce new sensitivity to
sparser metadata. Evidence:
[E19 validation result](../reports/experiments/coverage-stress-post-e19-validation.json).

### T26: Price presence prior (current best)

- Date: 2026-08-29 (run), merged and re-measured on the E19 stack
  2026-08-30.
- Numbering note: developed on `feat/hs` in parallel with E13-E20, before
  those existed locally. Its original standalone result was measured on the
  E11 stack (TechnicalScore `0.841838` -> `0.858595`). Every number below is
  the post-merge re-measurement on top of E19, which is the only comparison
  that describes this tree.
- Origin: the two catalog fields E11 left unused. `price` and
  `average_rating` were both measured against the targets before either was
  weighted.
- Measurement: 89.0% of the 200 public targets carry a price against 21.1%
  of the 50,000-item catalog. The gap is not popularity in disguise --
  inside the catalog's top popularity decile, where 173 of 200 targets
  already sit, only 31.6% of products are priced against 89.0% of targets.
  A priced listing is an active listing, and only active listings get
  purchased.
- Change: `_has_price` / `_average_rating` in `starter/reranker.py` and
  `price_weight` / `rating_weight` on `rerank_candidates`;
  `starter/agent.py` collects both fields during index construction into
  their own dicts, leaving the FTS5 `bm25()` column weights untouched.
  Presence only -- the price value is never read. A bonus, never a filter:
  11% of targets have no price, so excluding unpriced candidates would make
  those sessions unwinnable.
- New tests: 6 (`PricePresencePriorTest`, `AverageRatingPriorTest`).
  143/143 project tests pass.
- Commands:

  ```powershell
  python -m unittest discover -s tests -v
  python -m evaluator.local_evaluator
  ```

- Weight re-swept on the merged stack, not carried over. Validation is the
  80-session held-out split (`techjam-clarification-v1`):

  | Price weight | Validation | Full | HitRate@10 | MRR |
  | ---: | ---: | ---: | ---: | ---: |
  | 0.0 (E19) | 0.883582 | 0.868476 | 0.980 | 0.715919 |
  | 1.0 | 0.892926 | 0.873253 | 0.980 | 0.728177 |
  | **2.0** | **0.895201** | **0.880670** | 0.980 | **0.756899** |
  | 3.0 | 0.894515 | 0.878848 | 0.980 | 0.749825 |
  | 5.0 | 0.892311 | 0.871899 | 0.975 | 0.736331 |

  Validation and full agree on `2.0` on this stack. They did not agree on
  the pre-merge E11 stack, where validation favoured `3.0` and `2.0` was
  chosen as the point all three splits agreed on; the merge removed that
  disagreement rather than creating it.
- Result: HitRate@10 `0.980 -> 0.980`, MRR `0.715919 -> 0.756899`, MTTC
  `2.815 -> 2.820`, TechnicalScore `0.868476 -> 0.880670` (`+0.012194`).
  **No scenario hit rate moves** (Buying `0.9875`, Browsing `1.0000`,
  Intent Override `0.933333`, Boundary `0.9000`), and MTTC is `0.005`
  worse. The entire gain is MRR.
- Decision: **Keep. New current best.** `PRICE_WEIGHT = 2.0` is the `Agent`
  default. The gain being pure MRR is consistent with the mechanism: E19's
  phrase bonus decides which candidates surface, and the price prior orders
  the ones that surface tied.
- `RATING_WEIGHT` ships at `0.0`. The rating prior is implemented and
  unit-tested but disabled: once popularity is controlled for, the
  target/catalog rating gap collapses from `0.285` to `0.084`, and its two
  splits disagree about the weight. It was never swept jointly with price,
  so the standalone rating numbers are not a guide for enabling it on top
  of price `2.0`.
- Commit/branch: `fe86b63` on `feat/hs`.
- **Coverage-stress result: the prior's sign reverses.** Run through T25's
  diagnostic (2026-08-30). The stress build masks `price` on 136 of 178
  priced targets, leaving 42, while masking `rating_number` on **zero**
  (100% catalog coverage), so the popularity prior is untouched and the
  whole delta is attributable to price.

  | Catalog | E19 (price 0.0) | E21 (price 2.0) | Price prior gain |
  | --- | ---: | ---: | ---: |
  | Official | 0.868476 | **0.880670** | **+0.012194** |
  | Coverage-stress | 0.873848 | 0.853574 | **-0.020274** |

  Validation agrees and is sharper: `+0.011619` official, `-0.027275`
  stress. This is not a signal that weakens -- a vanishing signal would
  land near zero. It **inverts**: with only 42 targets priced, the flat
  `2.0` bonus systematically promotes non-target priced candidates above
  the 136 targets whose price was stripped. It is also the only
  measurement in which the price prior moves HitRate@10 at all: `0.980 ->
  0.965` under stress, **3 sessions lost** (2 Buying, 1 Browsing) that E19
  finds on the same catalog. Boundary and Intent Override are unchanged.
- Limitations: the 89%/21% price gap is a property of how the public set
  was built, and the two catalogs bracket the unknown private set. If the
  800 private targets are priced like the public ones (89%), E21 is worth
  `+0.012194`; if they are priced like the catalog (21%), it costs
  `-0.020274` -- a downside roughly 1.7x the upside in magnitude. Official
  metrics still select methods (see T25: stress is a diagnostic and does
  not replace the official score), so E21 stands as current best, but its
  margin is conditional on a property of how the public set was built in a
  way no other retained layer's is. `PRICE_WEIGHT` should not be re-tuned
  against the stress catalog: T25 warns that diagnostic can be overfit by
  repeated use, and sweeping against it would convert an independent check
  into another fitted split. Evidence:
  [price and rating priors](../reports/experiments/price-rating-prior.md),
  [E21 weight sweep](../reports/experiments/price-prior-e21.json),
  [E21 coverage-stress](../reports/experiments/coverage-stress-e21.json).

### T27: Constraint satisfaction on all routes (current best)

- Date: 2026-08-30.
- Origin: a proposal to rebalance constraints against priors, in two parts --
  make the satisfaction bonus large enough that priors cannot overturn it,
  and weight constraints by the turn they arrived on.
- Premise checked first: the popularity term spans `3.08` (median) to `9.73`
  (p99) across the catalog, a spread of `6.65` against E13's
  `COMPLETENESS_BONUS = 4.0`. The described failure is arithmetically real,
  but only when the *completing* term lands in a cheap field -- an exact
  match earning full title weight on every constraint wins on match score
  alone. Both cases pinned by `PriorProofCompletenessTest`.
- **Prior-proofing was rejected: it does nothing.** Raising the bonus to
  `8.0` or `16.0` on the Buying route produced `+0.000000` to six decimals,
  byte-identical output. The constructed failure never decides a session in
  the Buying pools that actually occur.
- The gain came from a change that was not proposed: applying the bonus to
  **Browsing** sessions, which E13 excluded. A Browsing session opens vague
  but discloses concrete constraints once it answers a clarification
  question.

  | Arm | Validation delta | Full delta |
  | --- | ---: | ---: |
  | bonus 8 / 16, Buying only | +0.000000 | +0.000000 |
  | **all routes, bonus 4 (shipped)** | +0.003214 | **+0.004071** |
  | all routes, bonus 16 | **+0.003339** | +0.003288 |
  | all routes, bonus 40 | +0.003339 | +0.003288 |

  Magnitude does matter stacked on route generalization, but by `+0.000125`
  validation, saturating at 16.0 (identical at 40.0). Roughly 26:1 in favour
  of the route change.
- Change: `COMPLETENESS_ALL_ROUTES = True` in `starter/agent.py`, with
  `COMPLETENESS_BONUS` unchanged at `4.0`. `bonus 4` was shipped over
  `bonus 16` because it wins the full set (`+0.000783`) and both
  coverage-stress measures, losing only validation by `+0.000125`.
- New tests: 2 in `test_conversation_state.py`, including a negative control
  that sets `completeness_all_routes = False` and asserts the opposite
  ordering on the same Browsing session, plus 5 in `test_reranker.py`.
  158/158 pass.
- Result: HitRate@10 `0.980 -> 0.980`, MRR `0.756899 -> 0.770470`, MTTC
  unchanged at `2.820`, TechnicalScore `0.880670 -> 0.884741`
  (`+0.004071`). No scenario hit rate moves. Pure MRR, as a reordering rule
  that never changes the candidate pool should be.
- **Coverage-stress: holds, and helps more.** Official `+0.004071`, stress
  `+0.005588` (validation `+0.003214` / `+0.005250`). The opposite of E21,
  whose gain reverses under the same diagnostic. Constraint satisfaction is
  a statement about the conversation, not about catalog metadata, so
  degrading target metadata cannot invert it. It does not recover the 3
  sessions E21 loses under stress; HitRate@10 stays `0.965` there.
- Decision: **Keep. New current best.**
- Limitations: reorders only, never rescues a missed session. The
  `4.0`-versus-`16.0` choice rests on `+0.000783` full against `+0.000125`
  validation and was decided on parsimony, not a decisive margin. Evidence:
  [constraint satisfaction on all routes](../reports/experiments/constraint-satisfaction-routing.md),
  [sweep](../reports/experiments/constraint-rebalance.json),
  [E22 dual-catalog run](../reports/experiments/constraint-satisfaction-routing.json).

### T28: Turn-recency term weighting (rejected, monotonic)

- Date: 2026-08-30.
- Hypothesis: later answers are more specific than the opening category, so
  a term that arrived on turn 4 should outweigh one from turn 1.
- Change: `term_weights` on `rerank_candidates`, scaling each term by
  `1 + recency_weight * (arrival_turn - 1)`. The agent records the first
  turn each surviving term entered the query, rebuilt against
  `unique_terms` every turn so an override that drops a term also drops its
  arrival record.

  | `recency_weight` | Validation delta | Full delta | HitRate@10 |
  | ---: | ---: | ---: | ---: |
  | 0.1 | -0.000217 | -0.000762 | 0.980 |
  | 0.25 | -0.003244 | -0.005046 | 0.980 |
  | 0.5 | -0.016098 | -0.015506 | 0.970 |
  | 1.0 | -0.026436 | -0.031340 | 0.960 |

- Mechanism traced: retrieval is an accumulating OR query, so the opening
  category term is what holds the candidate pool on-topic. Down-weighting it
  relative to later details widens the pool rather than sharpening it, which
  is why HitRate falls from `0.5` upward.
- Also negative under coverage-stress (`-0.001824` full), and combining it
  with E22 was worse than E22 alone (`+0.002876` full against `+0.004071`).
- Decision: **Reject.** No peak and no plateau -- a clean monotonic decline
  on both splits. Code path retained at `RECENCY_WEIGHT = 0.0` for ablation,
  as with `RATING_WEIGHT` and the `entropy` clarification policy.

### T29: Constraint ledger Stage 0, override-state correctness (rejected)

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

### T30: Constraint ledger Stage 1, append-only state and query projection (keep)

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

### T31: Constraint ledger Stage 2, weighting and the information-gain probe

- Date: 2026-08-30
- E24-C1, term weighting by source: the ledger records whether a constraint was
  volunteered or answered; `answered_weight` scales the latter in the reranker.
  Validation by weight: `0.6` `0.836582`, `1.0` (off) `0.853190`, `1.2`
  `0.851524`, `1.5` `0.850040`. The optimum is the off position on both sides.
  Reject. `term_weights` and `ConstraintLedger.projection_weights` are retained
  as no-ops at their defaults, per the T13 precedent that kept `idf`.
  `decay_lambda` stays `0` and was never swept: the public set contains no
  signal from which to fit a decay rate.
- E24-C, information-gain probe: retrieval is a pure function of the projected
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
- Dead turns: `163/586` at E11, `140/557` at E24-B, `85/504` at E24-C. The count
  of sessions containing a dead turn is unchanged at 57, correctly: the probe
  cannot prevent the first one, because that turn is the signal.
- Limitation: this is the experiment most exposed to the simulator. The gain
  depends on the evaluator answering `other` with up to two undisclosed
  constraints, which T9 documented and warned may not hold privately. The
  mechanism is a general strategy; the size of the gain is not guaranteed to
  transfer. If the private simulator treats `other` like any other attribute,
  this degrades toward E24-B rather than breaking.
- Evidence: [Stage 2 report](../reports/experiments/constraint-ledger-stage2.md).

### T32: Rank-margin diagnostic and the catalog quality prior (rejected)

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
- E25-A: `average_rating` has full catalog coverage and appeared in no scored
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

### T33: Exhaustion-triggered catalog IDF (rejected, with a mechanism)

- Date: 2026-08-30
- Hypothesis: the three in-pool Buying misses all carry hard constraints made
  of generic material words, and the reranker weights every term identically.
  E8 rejected catalog IDF applied unconditionally and E10 rejected it routed on
  an override signal; this applies it on a third signal, the E24-C
  information-gain counter, which is a perfect predictor of failure on the
  public set. The reasoning was that discounting a term while information is
  still arriving risks discarding a constraint the customer has not finished
  expressing, whereas once the counter fires the term list is final.
- Result: HitRate@10 `0.980`, MRR `0.698381`, MTTC `2.540`, TechnicalScore
  `0.868714` at thresholds 1 and 2 alike, identical in every digit to E24-C.
  **Zero of 200 sessions changed hit, hit turn, or rank.** The mechanism was
  verified to fire: per-term multipliers move from a flat `1.0` to a `0.93` to
  `7.42` spread on triggering turns.
- Why: IDF moves the target *away* from the Top-10. Pool position on the stuck
  turn, without IDF then with it: `public_0054` `11 -> 27`, `public_0161`
  `17 -> 30`, `public_0179` `28 -> 27`, `public_0020` outside the pool either
  way. The direction of the hypothesis was wrong, not just its size.
- Mechanism, and the reason E8 and E10 also failed: the rarest words in the
  query are the evaluator's own phrasing, not the customer's constraints. For
  `public_0054` the three highest IDF weights go to `matters` (29 products,
  `7.42`), `requirement` (36, `7.21`) and `key` (612, `4.41`), all from "A key
  requirement is:" and "For that, what matters is:". `women`, the customer's
  actual stated attribute, receives the lowest weight in the query, `0.93` --
  eight times less than `matters`. Rarity and informativeness are different
  quantities here, so any rarity-based weighting promotes conversational
  scaffolding over stated constraints. E8 and E10 recorded the outcome; none of
  the reports recorded this cause.
- Interaction with T29: Stage 0 measured that *removing* those same template
  words costs two intent_override sessions, because they widen the FTS5 `MATCH`
  expression and change pool composition. T33 measures that *weighting* them is
  worse than weighting nothing. The template words must therefore be present
  and unweighted, which is what the retained agent already does. Neither half
  is obvious alone, and a query-cleaning step cannot be evaluated independently
  of a weighting step.
- Decision: reject. `exhaustion_idf` and `_effective_term_weights` removed;
  `starter/agent.py` is byte-identical to E24-C. The optional `idf` argument on
  `rerank_candidates` stays, per T13.
- Next step: no term-weighting scheme derived from catalog statistics is likely
  to work while the query contains evaluator phrasing. A measure computed over
  product vocabulary alone would have to come first, and T29 shows that simply
  deleting the conversational vocabulary costs sessions.
- Evidence: [exhaustion-triggered IDF](../reports/experiments/exhaustion-triggered-idf.md).

### T34: Implicit-rejection reranking (current best)

- Date: 2026-08-30
- Hypothesis: T32 and T33 both failed to move the four stuck sessions, and
  widening the pool was ruled out by pool-position data. What remained unused
  was negative evidence the conversation supplies for free: a shopper who saw
  ten products and kept talking has implicitly declined them, and returning the
  same ten is the one outcome that cannot succeed. The ledger recorded what the
  customer said but not what the agent showed.
- Change: count what has been shown per session and, only once the
  information-gain counter says the conversation is stuck, subtract
  `rejection_weight * times_shown` from the rerank score. While new constraints
  are arriving the ranking improves for legitimate reasons and is left alone.
- Second change: a stuck agent previously asked `other` every remaining turn.
  In this evaluator `other` is a strict superset of every named attribute --
  `customer_reply` short-circuits on `attribute == "other"` -- so one empty
  answer proves nothing is left. That is a property of the simulator, not of
  shoppers, and hard-coding it would not transfer. The stuck agent now asks
  `other` once and then cycles named attributes.
- Sweep validation: `0.0` `0.867378`, `0.5` `0.875253`, **`1.0` `0.884128`**,
  `2.0` `0.884878`, `4.0` `0.885128`, `8.0` `0.885753`, `16.0` and `64.0`
  identical to `8.0`.
- Result at the retained weight `1.0`: HitRate@10 `0.995`, MRR `0.694964`,
  MTTC `2.465`, Efficiency `0.8535`, TechnicalScore `0.876689`. Buying
  `0.950000 -> 0.987500`; Browsing, Boundary and Intent Override all
  `1.000000`. Three of the four misses recovered.
- **The retained weight is not the highest-scoring one.** The curve is monotone
  and saturates at `8`, where the penalty exceeds any plausible difference in
  match quality and every unshown candidate outranks every shown one regardless
  of how well it matches. `docs/submission_rules.md` requires recommendations
  "ordered best to worst"; that is a mechanical exclusion, not an ordering. At
  saturation the recovered sessions report ranks `1`, `2`, `3` for items the
  agent ranks 11th, 17th and 28th. At `1.0` the penalty is about one
  field-weight unit against match scores of 7 to 30, so it breaks near-ties
  only, and a strongly matching shown item still outranks a weakly matching new
  one. The invariant is locked by `test_relevance_still_outranks_novelty`. The
  cost of declining the saturated region is `0.001625`.
- Honest accounting: part of the gain is still earned by removing competitors
  rather than by ranking better. MRR in fact falls slightly
  (`0.698381 -> 0.694964`) while HitRate carries the improvement, which is the
  opposite of what rank inflation would produce. The sweep lacks T15's shape --
  development and validation do not peak independently and there is no plateau
  -- so the evidence is weaker than the popularity prior's.
- Decision: keep at `rejection_weight = 1.0`. Constructor defaults unchanged;
  an unflagged `Agent()` still reproduces E11 at `0.841838`.
- Safety of the penalty: the target is never penalised on the turn it is
  found, across 199 hits with no exception. For Buying, Browsing and Boundary
  this is a guarantee, not an observation: a turn's own recommendations are
  recorded as shown only after that turn has been scored, and the evaluator
  ends the session the moment the target enters the Top-10, so the target's
  shown count is provably zero at every scoring call. Intent Override is the
  exception, because a pre-override hit does not end the session; 27 of 30
  targets are shown pre-override and 13 of 30 carry a penalty at some call, up
  to `2.0`. None is penalised when found, because the override message brings a
  constraint that resets the counter. That part is empirical, 30 of 30, and a
  differently timed private override could break it.
- Limitations: three recovered sessions out of 80 Buying. `public_0020` remains
  unreachable at pool position 187. The penalty counts showings, not positions.
- Evidence: [implicit-rejection reranking](../reports/experiments/implicit-rejection-reranking.md).

### T35: Stuck-path clarification policy (rejected on behaviour, not score)

- Date: 2026-08-30
- Question: when the information-gain counter says the conversation is stuck,
  the agent bypasses `select_attribute` entirely and round-robins over
  `DEFAULT_ATTRIBUTE_ORDER`. That was the crudest decision in E26 and it was
  never tested. Routing the branch back through the candidate-aware policy,
  with the asked set dropped so it may repeat, should in principle pick a
  better question than blind rotation.
- Result: identical in every digit -- TechnicalScore `0.876689`, HitRate@10
  `0.995`, every scenario unchanged.
- Why it cannot be measured here: across 200 sessions and 492 turns, the branch
  fires 10 times in 2 sessions (`2.0%`). 404 turns (`82.1%`) take the normal
  Layer-4 path and 78 (`15.9%`) are the first stuck turn, which asks `other`
  under both variants. Of the two affected sessions, `public_0020` is
  unreachable at pool position 187 and `public_0179` hits either way. E26 had
  already all but eliminated the persistently-stuck state: before it, four
  sessions were stuck for six turns each.
- Decided on behaviour instead. Under the policy variant a stuck agent asks the
  **same attribute every turn** -- `public_0020` asks `color` five times,
  `public_0179` asks `material` five times -- because which attribute best
  separates the candidates is stable even as the rejection penalty shuffles
  individual products. That reintroduces, in a new form, the repetition the
  branch exists to avoid. Round-robin varies genuinely: `material, size, style,
  feature, use_case`.
- Decision: reject. The `stuck_clarification` parameter was removed; round-robin
  stays and now carries the reasoning in a comment. Adds
  `test_a_persistently_stuck_agent_never_repeats_a_question`, which locks the
  property that decided it.
- Value: this converts a crude fallback into an evidenced one. The round-robin
  is not laziness; it is the only variant tested that guarantees a stuck
  conversation stops asking one dead question.


### T36: Merging the two parallel lines (current best)

- Date: 2026-08-30
- Two lines were developed in parallel without knowledge of each other.
  `feat/hs` produced E12-E21, which improved rank quality: Buying/Browsing
  routing, semantic reranking, the phrase bonus, the price prior.
  `experiment/constraint-ledger` produced E22-E27, which improved
  conversational coverage: the append-only constraint ledger, the
  information-gain probe, the implicit-rejection penalty.
- They turned out to be complementary rather than overlapping.

  | Metric | E21 alone | E26 alone | Merged |
  | --- | ---: | ---: | ---: |
  | HitRate@10 | 0.980 | **0.995** | **0.995** |
  | MRR | **0.756899** | 0.694964 | **0.776613** |
  | MTTC | 2.820 | **2.465** | **2.400** |
  | TechnicalScore | 0.880670 | 0.876689 | **0.902484** |

  Every metric lands at or better than the best of either side. MRR is
  `+0.019714` above E21 alone and MTTC `-0.065` below E26 alone, so the merge
  is not simply the union of two disjoint gains.
- Merge decisions worth recording:
  - `starter/reranker.py` took the `feat/hs` version as the base. Its
    restructuring (`_best_weight_by_term` extracted, `_match_score` signature
    changed, five new parameter groups) is intact; `shown_penalty` was added as
    one more subtracted term. The scoring function now carries seven terms.
  - E24-C1's `term_weights` machinery was removed entirely rather than merged.
    It was already a measured no-op and would have been dead code after the
    restructuring.
  - E13's `_classify_route` call had to be moved by hand. The automatic merge
    did not drop it -- it *relocated* it. The call sat next to
    `accumulated_slots` in `feat/hs`, that block became `_advance_slots` in the
    refactor, and the merge followed the context and carried the call in with
    it. But `_advance_slots` only runs under `state_model="slots"`, which is no
    longer the default, so the default ledger path never classified a route and
    18 tests failed with `KeyError`. The call now lives in `respond()`, which
    both state models pass through. A clean automatic merge is not evidence
    that nothing moved somewhere it does not run, and that failure mode is
    harder to spot than deletion: the code is still there and still greps.
  - E13's `required_terms` now reads `self._session_slots[session_id]` instead
    of a local. Under the ledger that resolves to `slots_view()`, which returns
    only **active** entries, so a revoked constraint is never required of a
    candidate. Neither line had this behaviour alone; it falls out of the
    combination.
- Retrieval is unchanged. Both attempts to replace it were rejected on their
  own line: E16 dense-only scored `0.600216` and E17 RRF `0.830909`, against
  BM25's baseline. `retrieval_mode` stays `"bm25"`.
- Automated tests: 143 and 137 separately, 195 merged, all passing.
- **Cross-environment verification.** The merge was measured on
  `scikit-learn 1.7.2` (Python 3.10) and independently re-run on the pinned
  `scikit-learn 1.9.0` (Python 3.12). Both produce `0.902484` with identical
  HitRate@10 `0.995`, MRR `0.776613` and MTTC `2.400`, so E18's TruncatedSVD
  values are stable across those versions and the reported score does not
  depend on the environment it was measured in.

### T37: Merged-system ablation

- Date: 2026-08-30
- Purpose: the `Δ` column records what a method bought the day it was added.
  After merging two parallel lines that is no longer a usable ranking of what
  matters, both because E22-E27's deltas are measured against E11 and because
  a mechanism can stop paying once later mechanisms rescue the same sessions.
  Each retained mechanism was removed from the merged agent one at a time and
  the official evaluator re-run.
- Harness check: removing the whole constraint-ledger stack reproduces E21 at
  `0.880670` to six decimals.
- Marginal contribution, full system `0.902484`:

  | Mechanism | Marginal |
  | --- | ---: |
  | Popularity prior (E11) | **-0.060171** |
  | Constraint ledger (E24-B) | -0.012000 |
  | Price presence prior (E21) | -0.012368 |
  | Information-gain probe (E24-C) | -0.009731 |
  | Phrase bigram bonus (E19) | -0.009239 |
  | Buying/Browsing routing (E13) | -0.004612 |
  | Semantic reranking (E18) | **-0.001723** |
  | Implicit-rejection penalty (E26) | **-0.000083** |

- **The popularity prior dwarfs everything built since.** Removing E11 costs
  three times the next largest mechanism and roughly the sum of all the others.
  Ten experiments across two parallel lines have collectively added less than
  that one prior, and any description of this system that omits that is
  misleading about where its performance comes from.
- **E26 has stopped paying.** `0.000083`, with MRR fractionally higher without
  it. It was worth `+0.014050` on its own line; the three Buying sessions it
  rescued are now rescued earlier by the phrase bonus, the price prior and
  semantic reranking, so it fires after the problem is already solved. Removing
  it would also retire the only argument this system needs about the "ordered
  best to worst" submission rule.
- **E18 costs the project its entire dependency footprint for `0.001723`.**
  `starter/agent.py` imports `starter/dense.py` unconditionally, so
  scikit-learn and its transitive dependencies are required merely to import
  the Agent. Whether that trade is worth making is a feasibility judgment for
  whoever owns that experiment, not a score question.
- Limitations: single removals only, so interactions are unmeasured and the
  marginal contributions do not sum to the total -- they overlap wherever two
  mechanisms rescue the same session. Near-zero here means redundant against
  the mechanisms currently present, not useless on the private 800.
- Evidence: [merged-system ablation](../reports/experiments/merged-system-ablation.md).

### T38: Retiring the implicit-rejection penalty

- Date: 2026-08-30
- Reason: T37 measured E26's marginal contribution in the merged system at
  `0.000083`, with MRR fractionally higher without it. On its own line it was
  worth `+0.014050`; the three Buying sessions it rescued are now rescued
  earlier by the phrase bonus, the price prior and semantic reranking, so the
  mechanism fires after the problem has already been solved.
- Second reason, independent of score: E26 was the only part of this system
  that needed an argument about `docs/submission_rules.md` requiring
  `recommendations` to be "ordered best to worst". The argument was sound at
  weight `1.0` -- the penalty was about one field-weight unit against match
  scores of 7 to 30, so a clearly better match still outranked a merely newer
  one, and `test_relevance_still_outranks_novelty` locked that. But not having
  to make the argument is better than making it for `0.000083`.
- Removed: `rejection_weight`, `Agent._shown_penalty`, `Agent._session_shown`,
  the `REJECTION_WEIGHT` constant, and `rerank_candidates`'s `shown_penalty`
  parameter. The reranker is back to six scoring terms.
- Kept: the information-gain probe and everything it does, including asking an
  open question once and then cycling named attributes rather than concluding
  the customer has nothing left to say. Two tests that protected probe
  behaviour rather than the penalty moved to `StuckConversationTest`.
- Result: `0.902401`, exactly T37's prediction. HitRate@10 `0.995`, MRR
  `0.776669`, MTTC `2.405`; Buying `0.987500`, Browsing, Boundary and Intent
  Override all `1.000000`. No scenario changes.
- Automated tests: 195 before, 188 after.
- Note on method: this is the first mechanism in the project retired for having
  *stopped* paying rather than for never having paid. The matrix cannot surface
  that case, because a row's `Delta` is fixed on the day it is written. Only a
  periodic ablation can, and one is worth running again whenever a new
  mechanism lands.


### T39: Second merge with `feat/hs` (current best)

- Date: 2026-08-30
- `feat/hs` pushed E22 (constraint satisfaction on all routes) and E23
  (turn-recency term weighting, rejected) after the first merge. Merging them
  in raises the combined agent from `0.902401` to **`0.906943`**: HitRate@10
  `0.995` unchanged, MRR `0.776669 -> 0.791810`, MTTC `2.405` unchanged, every
  scenario unchanged. E22's `+0.004542` here is smaller than the `+0.004071` it
  measured on its own line, which is what a bonus overlapping with existing
  ranking should look like.
- Conflicts were small: one in `starter/agent.py` (both sides added constructor
  assignments, both kept) and five in this file, all numbering.
- **Numbering collided a second time.** This line had already been renumbered
  to E22-E26 after the first merge; `feat/hs` then took E22 and E23, and T27
  and T28. It is renumbered again, by `+2`: E24-A/B/C1/C, E25-A/B, E26, E27,
  E28, and T29-T38. Only this line's numbers were rewritten; `feat/hs` numbers
  were left exactly as pushed.
- The root cause is that this branch has not been pushed, so the other line
  cannot see which numbers are taken. Renumbering again on the next push is
  likely unless the branch lands or a block is reserved. This is a process
  observation, not an experiment result.
- **E23 independently reproduces E24-C1's rejection.** `feat/hs` scaled each
  query term by `1 + w * (arrival_turn - 1)` and found it monotonic, so the
  optimum was `w = 0`. This line scaled answered constraints against
  volunteered ones and found the optimum at the off position. Two different
  formulations of "weight query terms by when or how they arrived", measured
  independently on two branches, both landing on no weighting at all. That is
  stronger evidence than either result alone.
- Automated tests: 195, all passing.

### T40: Deferring the scikit-learn import

- Date: 2026-08-30
- Motivation: T37 measured E18 semantic reranking at a marginal `0.001723`
  while it was the reason for the project's entire third-party dependency.
  `starter/agent.py` imported `starter/dense.py` at module scope, so
  scikit-learn, scipy, joblib and threadpoolctl were required merely to
  *import* the Agent -- including for configurations that never build a dense
  index.
- Change: the import moved inside `_build_index`, behind the
  `_needs_dense_index` guard that already existed. One line, no behavioural
  change to any scored path.
- Result: `0.906943` unchanged, all scenarios unchanged, 197 tests passing.
  The default configuration still requires scikit-learn, because E18 is on by
  default. What changed is that `Agent(semantic_weight=0.0,
  retrieval_mode="bm25")` -- which includes the E11 reproduction and every
  ablation arm that turns semantics off -- now imports and runs on the standard
  library alone.
- Two tests pin both directions: a non-semantic Agent builds with
  `starter.dense` blocked, and the default Agent still raises `ImportError`
  with it blocked. The second matters more than the first: it is what stops the
  deferral from quietly turning E18 off.
- This is a Feasibility and Practicality change rather than a score change. It
  does not remove the dependency; it makes it proportionate to what actually
  uses it, so the claim "this agent runs on the standard library" stays true
  for every configuration that does not opt into semantics.

### T41: Query representation, both halves (both rejected)

- Date: 2026-08-30
- Context: a proposal to build a query-understanding module holding a
  structured representation and a semantic one separately, in the style of
  Amazon's query reformulation and hint-augmented reranking work, with LLM
  decomposition feeding deterministic retrieval.
- First finding: **the separation already exists.** The agent builds four query
  representations per turn -- `slots_view()` for the completeness bonus, an
  `OR` expression for FTS5, a space-joined bag for the dense index, and
  bigrams of the raw message for the phrase bonus. What was missing was any
  *rewriting*.
- **E29, slot-projected semantic query.** The dense index was being handed the
  raw accumulated bag including evaluator phrasing
  (`tees blouses tunics hand wash only what matters polyester 60`). Projecting
  only active slotted entries in title order gives `blouses tees tunics
  polyester`. Result: `0.906943 -> 0.906993`, `+0.000050`. Rejected.
- The number that matters is the ceiling, not the result. Turning the semantic
  term off entirely costs `0.001871`, and `query_text` feeds nothing else, so
  **any** rewrite of it competes for that budget. The projection took 2.7% of
  it. An LLM-generated query would compete for the same `0.001871` while
  costing a model dependency, tokens, latency and the project's
  `usage: {prompt_tokens: 0}` property. That settles the LLM-rewrite question
  without building it.
- **E30, hard/soft separation.** The hidden hard/soft labels turn out to be
  exactly observable from the evaluator's wording: `"A key requirement is:"`
  precedes a hard constraint 80 times out of 80, the override's
  `"What I need is:"` 30 out of 30, and an unmarked turn-1 clause is soft 30
  out of 30. Zero errors over 110 occurrences. This is template reading, the
  mirror image of E25, where catalog IDF weighted `matters`, `requirement` and
  `key` highest for the same reason.
- Result: `0.906943 -> 0.904602`, `-0.002341`, entirely MRR. Rejected.
- Mechanism: the completeness bonus rewards matching *every* known constraint,
  and its value is that this is hard. Requiring only the hard constraints drops
  `required_terms` from 1.76 to 1.36 per turn and raises the candidates earning
  the bonus from 60 to 64.8 of 100. **We widened the holes in a sieve.** E22 is
  the counter-example that confirms it: extending the same bonus to Browsing
  was worth `+0.004071` because it widens *where* the bonus applies while
  keeping it equally strict. Extend it, never loosen it.
- Side finding that closes two earlier experiments: `source` (volunteered vs
  answered) is a poor proxy for hard/soft. Volunteered turn-1 constraints are
  73% hard, answered ones 66.7%, against a 70.5% base rate. That is why
  E24-C1's `answered_weight` and E23's `recency_weight` both swept to zero --
  **both were proxies for a distinction their signal does not carry.**
- Graceful degradation was built and verified: with no marker detected the hard
  set is empty and `required_terms` is untouched, so an unmarked conversation
  behaves exactly as before. It is not what decided the experiment; the
  mechanism is wrong even when detection is perfect.
- **Nothing was retained.** All three switches were removed along with the
  ledger's `strength` field, the marker detection and `hard_surfaces()`;
  `starter/agent.py` and `starter/ledger.py` are byte-identical to the branch
  point. Keeping the detection was considered, on the argument that `strength`
  is data rather than behaviour like `source` -- and rejected on the T3
  precedent. That precedent is what makes this ledger trustworthy, `source` is
  a documented part of the ledger's design where `strength` would have been the
  residue of a failed experiment, and nothing had ever read `hard_surfaces()`.
  The marker table above is the product; the six lines that implemented it are
  reconstructible from this entry.
- What this bounds: semantic scoring is worth `0.001871` and the completeness
  bonus `0.009154`, so those are the ceilings for improving their respective
  inputs, and E20 showed that changing the lexical query costs sessions. In a
  system whose largest single mechanism is a popularity prior worth `0.060`,
  query understanding is not where the remaining headroom lives.
- **E30-A, the opposite construction.** T41's own limitation named it: keep
  `required_terms` and add a *separate* bonus over the hard subset -- stricter,
  not looser. Measured at `0.906943`, identical to every digit, and for the
  opposite reason. `hard_surfaces()` marks every token of a marked message,
  including the `I'm looking for {category}` clause, so the hard set runs 5.22
  terms wider than `required_terms`; demanding all of them is satisfied by
  `0.1` candidates of 100. The bonus went to nobody.
- The two failures bracket the mechanism. `1.36` terms earns it 64.8 times of
  100 and loses `0.002341`; `1.76` terms earns it 60.0 times and is the
  baseline; `6.98` terms earns it 0.1 times and changes nothing. **The
  completeness bonus sits on a sweet spot** -- few enough must earn it to
  discriminate, not so few that nobody does. Both sides are worse. That is also
  why E22 worked: extending it to Browsing changes *where* it applies without
  touching how hard it is to earn.
- Four variants of query representation were tested and all four rejected, each
  against a different wall: E29 against a `0.001871` ceiling, E30 against a
  sieve made too coarse, E30-A against one made too fine, and E20 (on the other
  line) against a fixed candidate pool that a widened query only dilutes. This
  is not "no good method was found"; it is four distinct mechanisms.
- Evidence: [query representation](../reports/experiments/query-representation.md).

  ## 5. Current automated test coverage

  | Test module | Tests | Behavior protected |
  | --- | ---: | --- |
  | `test_agent_reranking.py` | 3 | Agent reranks a larger candidate pool |
  | `test_bm25_diagnostics.py` | 3 | Rank, cutoff recall, first-turn measurement |
  | `test_catalog_profile.py` | 1 | Coverage meaning for empty collections |
  | `test_catalog_variants.py` | 5 | Official/stress/dual mode resolution and rebuild-on-stale |
  | `test_clarification.py` | 3 | Fixed/profile difference, candidate grounded-attribute selection, and `other` probe |
  | `test_clarification_ablation.py` | 2 | Multiple policies and splits on the real FTS5 evaluator |
  | `test_conversation_state.py` | 42 | Accumulation, negation, slot-aware override, routing, fallback behavior, policy selection and default |
  | `test_coverage_stress.py` | 11 | Deterministic masking, invariants, atomic writes, path-collision rejection |
  | `test_dense.py` | 11 | TF-IDF + SVD index build, projection, and search |
  | `test_dual_catalog_evaluation.py` | 2 | Official/stress/delta payload shape |
  | `test_evaluator.py` | 3 | Simulator replies and metric aggregation |
  | `test_experiment_results.py` | 2 | Split metrics, scenario metrics, TechnicalScore, and dual deltas |
  | `test_experiment_split.py` | 1 | Fixed split size, stratification, and no dev/validation overlap |
  | `test_gazetteer.py` | 16 | Vocabulary mining, normalization, coverage, and one-slot precedence |
  | `test_popularity_sweep.py` | 2 | Weight/split/difficulty rows and dual-catalog deltas |
  | `test_reranker.py` | 29 | Complete-constraint priority, BM25 tie order, catalog IDF, popularity, price, rating, semantic, and phrase terms |
  | `test_session_viewer.py` | 9 | Transcript recording and viewer server |
  | `test_slots.py` | 5 | Whole-word, singular/plural, longest-match, and slot assignment behavior |
  | `test_ledger.py` | 23 | Slot assignment, `slot=None` survival, status transitions, restatement, projection order and cap, probe thresholds, slot/ledger equivalence |
| `test_session_trace.py` | 13 | Override keep/drop classification, normalization loss, dead-turn detection, trace/evaluator agreement |
| **Total** | see below | Run the suite; per-module counts have drifted |

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

### T42: Routing, then the first field-weight sweep (one kept)

- Date: 2026-08-31
- Context: after E28 the score is `0.906193` and HitRate@10 is `0.995` -- one
  miss in 200 sessions. That caps coverage work at `+0.0025`, leaving MRR
  (`+0.063` available) and MTTC (`+0.028`) as the only headroom. Both are rank
  quality, so all three experiments below target ranking, not retrieval.
- **E31, route-conditional weights.** E22 set `COMPLETENESS_ALL_ROUTES = True`,
  which short-circuits the only reader of `_classify_route`; the route has been
  computed and unread since. Gave it a job: per-route semantic and popularity
  weights, aimed at Browsing, whose MRR (`0.735417`) was the largest remaining
  pool of loss.
- Diagnostic first: the classifier is **152/160 = `0.950`** accurate on
  Buying/Browsing, measured against the public set's own labels. Its errors are
  structural, not noise -- Buying constraints carrying no gazetteer term
  (`"A key requirement is: Imported."`), and Browsing category names containing
  slot words (`"Bras Sports Bras"`). The classifier was not the weak part.
- Result: the validation winner (`browsing popularity 0.6`, `+0.000750`)
  **reversed** on the full set to `-0.005428`, losing a session of HitRate. It
  raised Browsing MRR to `0.747445` exactly as intended and still lost overall.
  Rejected. `buying semantic 0.0` survived at `+0.000286`, below margins this
  project has rejected before (E6, E23).
- Mechanism: routing cannot buy coverage at `0.995`, and splitting weights
  already tuned across E11-E28 halves the evidence behind each without adding a
  signal the reranker lacked. E13 worked because completeness *added
  information*; re-weighting information already present does not. The honest
  reading of E13 -> E22 -> E31 is that Buying/Browsing routing has not paid
  since E22 removed its last live consumer.
- **E32, category field weight (kept, new best).** `FIELD_WEIGHTS` had never
  been swept. Its values come from E1's information-hierarchy reasoning and
  survived twenty-eight experiments untouched, while every other weight in the
  system was swept or triangulated.
- The ordering was backwards. `initial_message` composes the customer's opening
  line from `coarse_category(target.categories)`, so the category words in the
  query are **quoted verbatim from the target's own category path**, while
  title words are only ever incidental -- a target's title may share no term
  with anything the customer says. `categories` was `3.0` against `title`'s
  `4.0`. Raised to `6.0`.
- Result: `0.906193 -> 0.917406`, `+0.011213`, the largest gain since E19.
  Browsing MRR `0.735417 -> 0.787827`, Buying `0.810774 -> 0.840000`, no
  scenario losing a session. Boundary MRR regresses `1.000000 -> 0.911111`, one
  session of ten off rank 1.
- The asymmetry is the evidence, not the size: raising `title` instead is
  sharply negative (`-0.067204` at `6.0`), which is what the mechanism predicts
  and not what generic weight sensitivity would look like. Swept `2.0-10.0`;
  the gain plateaus across `4.5-6.0` and decays beyond `7.0`. Validation and
  full set agree on `6.0` -- every validation winner held this time, which is
  why E31 was run first and is worth reading alongside.
- **Transfer evidence, the strongest any retained layer carries.** Under the
  T25 coverage-stress catalog the gain *grows* to `+0.021101` and recovers
  three stressed sessions of HitRate@10 (`0.980 -> 0.995`). E21 is the
  counter-example: its `+0.012194` official gain becomes `-0.020274` there.
  The stress catalog masks `title`, `features`, `description`, `price` and
  `details` to catalog-wide rates but leaves `categories` at `1.00000`, so
  stripping the fields the customer only incidentally overlaps makes the one
  field they are guaranteed to quote carry more of the signal.
- **E32-A, n-gram phrase bonus (rejected).** E19's bigram bonus was the largest
  gain since E13, and the simulator derives constraints from the target's own
  `features`/`details` text, so longer verbatim runs should discriminate
  better. `extract_phrases(text, max_n)` generalises `extract_bigrams` to runs
  of `2..max_n` with credit scaled by run length; `max_n=2` reproduces E19
  byte for byte.
- Result: `+0.002446` standalone but `0.916631` in combination against E32's
  `0.917406` -- negative once the category weight is in. Identical from `n=3`
  upward, because customer utterances rarely contain a matching run longer than
  three words. Once category matching dominates, the extra phrase credit
  re-orders candidates the category weight had already separated correctly.
  Retained at the no-op default `PHRASE_MAX_N = 2` with its tests, so the
  measurement is reproducible and the parameter is one edit away.
- What E32 says about the other twenty-eight: every prior ranking experiment
  added a **new signal** -- popularity, price, semantic similarity, phrase
  adjacency, constraint completeness. This one adds nothing. It corrects a
  mis-stated reliability ordering among signals already present, which is a
  class of improvement the project had never looked for.
- Still unswept: `store` (`1.5`), and every weight jointly rather than one axis
  at a time around the E28 point.
- Commands:

    ```powershell
    python -m unittest discover -s tests          # 205 tests
    python -m evaluator.local_evaluator           # TechnicalScore 0.917406
    python -m scripts.build_coverage_stress_catalog
    python -m scripts.run_dual_catalog_evaluation
    ```

- Decision: Keep E32. Reject E31 and E32-A.
- Commit: `1a7af82` on `experiment/ngram-phrase-bonus`; E31 preserved on
  `experiment/route-conditional-weights`.
- Detailed evidence: [field weight sweep](../reports/experiments/field-weight-sweep.md).


  ### T43: Is BM25-only a private-set risk? (union rejected, diagnostic kept)

- Date: 2026-08-31
- Question raised before submission: everything retained was selected on a
  public set whose customers speak in a handful of fixed sentence frames. If
  private sessions are vaguer, a system tuned on literal overlap could fail
  where a semantic retriever would not -- in which case it is worth giving up
  public score for a hybrid.
- First correction: **the system is already hybrid at the ranking stage.**
  `SEMANTIC_WEIGHT = 1.0` since E18, so every candidate's score already carries
  a dense cosine term. Only *retrieval* is BM25-only, which scopes the exposure
  exactly: if BM25 never pools the target, no reranking can recover it.
- Built the missing diagnostic. T25 stresses the catalog; nothing stressed the
  customer. `analysis/query_stress.py` rewrites the message in flight while the
  unmodified evaluator drives the session.
- **The dependency is real and it is the category phrase.** Removing the
  simulator's sentence frames costs `0.001129`; swapping head nouns for
  synonyms costs `0.025636`; replacing the quoted taxonomy with "something"
  costs `0.150384` and 31 sessions of HitRate@10 (`0.995 -> 0.840`).
- **Hybrid does not fix it.** `retrieval_mode="union"` appends dense hits after
  the BM25 pool rather than E17's fuse-then-truncate, so BM25 recall cannot be
  displaced. It costs `0.004607` clean and buys `+0.001840` at the severe level
  -- one session -- while being net negative at the realistic one. Dense alone
  is catastrophic at every level (`0.399` at L2).
- Mechanism: `starter/dense.py` is TF-IDF + SVD, i.e. Latent Semantic Analysis
  over the same catalog text. It models term co-occurrence, so it is still
  lexical. When the query loses its informative content, LSA is no better off
  than BM25 -- the two degrade **together**, not complementarily. A pretrained
  sentence encoder might not, but network access may be disabled at scoring and
  downloaded weights are out of scope, so the alternative that would justify
  the trade cannot ship.
- **E32 is not the fragile bet it appears to be.** Its gain persists under
  synonym rewording (`+0.010585` against `+0.011213` clean) and is neutral when
  the category is removed entirely (`+0.000429`). It exploits a dependency the
  system already had rather than deepening it.
- How much the L2 number should worry us: less than its size suggests. The
  private set is scored by the same `evaluator/local_evaluator.py`, whose
  `initial_message` always emits `coarse_category(target.categories)`. L2
  requires replacing the simulator, not paraphrasing it. The realistic downside
  is the `0.026` of L3, and no available retrieval change reduces it.
- Decision: **submit `retrieval_mode="bm25"`.** Retain the diagnostic and the
  `union` mode as non-default, so the comparison is rerunnable.
- Commands:

    ```powershell
    python -m unittest discover -s tests
    python -m scripts.run_query_stress
    ```

- Detailed evidence: [query stress and hybrid retrieval](../reports/experiments/query-stress-and-hybrid-retrieval.md).

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
- [Price and rating priors](../reports/experiments/price-rating-prior.md)
- [Constraint satisfaction on all routes](../reports/experiments/constraint-satisfaction-routing.md)
- [Adaptive retrieval design](superpowers/specs/2026-08-29-adaptive-intent-aware-retrieval-design.md)
- [Constraint ledger design](designs/2026-08-30-constraint-ledger-design.md)
- [Constraint ledger Stage 0](../reports/experiments/constraint-ledger-stage0.md)
- [Constraint ledger Stage 1](../reports/experiments/constraint-ledger-stage1.md)
- [Constraint ledger Stage 2](../reports/experiments/constraint-ledger-stage2.md)
- [Rank-margin diagnostic](../reports/experiments/rank-margin-diagnostic.md)
- [Exhaustion-triggered IDF](../reports/experiments/exhaustion-triggered-idf.md)
- [Implicit-rejection reranking](../reports/experiments/implicit-rejection-reranking.md)
- [Merged-system ablation](../reports/experiments/merged-system-ablation.md)
- [Query representation](../reports/experiments/query-representation.md)

- [Field weight sweep](../reports/experiments/field-weight-sweep.md)
- [Query stress and hybrid retrieval](../reports/experiments/query-stress-and-hybrid-retrieval.md)
- [Route-conditional weights](../reports/experiments/route-conditional-weights.md)
- [Test gap audit](test_gap_audit.md)
