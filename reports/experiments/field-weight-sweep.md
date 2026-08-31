# Field Weight Sweep and N-Gram Phrase Extension (E32)

Date: 2026-08-31
Status: **Keep. New current best.** TechnicalScore `0.906193 -> 0.917406`
(`+0.011213`).

## Hypothesis

Two untested surfaces were left after E28.

**`FIELD_WEIGHTS` had never been swept.** The values in
`starter/reranker.py` — title `4.0`, categories `3.0`, features/details `2.0`,
store `1.5`, description `1.0` — come from E1's original "information
hierarchy" reasoning and were never revisited across twenty-eight experiments,
while every other weight in the system (popularity, price, rating, semantic,
phrase, completeness) was swept or triangulated.

The hypothesis that made this worth testing is structural, not "tune it and
see". The evaluator builds the customer's opening line as

```python
f"I'm looking for {coarse_category(categories[target])}. ..."
```

so the category words in the query are **quoted verbatim from the target's own
category path**. Title words are only ever incidental — a target's title may
share no term with anything the customer says. Categories is therefore the one
field with a guaranteed overlap with the query, and weighting it below title
inverts the reliability ordering.

**`extract_bigrams` stops at pairs.** E19's bigram bonus was the largest single
gain since E13 (`+0.018594`). Because the simulator derives a customer's
constraint from the target's own `features`/`details` text, a disclosed
constraint is close to a verbatim span of the target listing, so runs longer
than two words should be more discriminating still.

## Change

- `starter/reranker.py`: `FIELD_WEIGHTS["categories"]` `3.0 -> 6.0`. Nothing
  else in the mapping moves.
- `starter/reranker.py`: new `extract_phrases(text, max_n)`, a generalisation
  of `extract_bigrams` to contiguous runs of length `2..max_n`, with phrase
  credit scaled by `len(phrase.split()) - 1` so a 5-word span is worth four
  times a 2-word one. `max_n=2` reproduces `extract_bigrams` byte for byte.
- `starter/agent.py`: new `phrase_max_n` parameter, default `PHRASE_MAX_N = 2`.
  Retained at the no-op default — see Decision.

Retrieval, conversation state, clarification, and every other weight are
untouched.

## Keep/reject threshold

Pre-registered: keep if full-set TechnicalScore improves over `0.906193` with
no scenario losing more than one session of HitRate@10. Candidates selected on
the fixed `techjam-clarification-v1` validation split (80 sessions), then
confirmed on the full 200. E31 was rejected days earlier for a validation gain
that reversed on the full set, so full-set confirmation is treated as the
decision, not a formality.

## Validation split (80 sessions), baseline `0.913103`

N-gram depth:

| max_n | Score | Δ |
| ---: | ---: | ---: |
| 2 (E19 behaviour) | 0.913103 | — |
| 3 | 0.915281 | +0.002178 |
| 4, 5, 6, 8 | 0.915281 | +0.002178 |

Identical from `n=3` upward: customer utterances rarely contain a matching run
longer than three words, so the extra n-grams find nothing.

Field weights (title held at `4.0` unless stated):

| Configuration | Score | Δ |
| --- | ---: | ---: |
| title 6.0 | 0.845899 | -0.067204 |
| title 8.0 | 0.786545 | -0.126558 |
| categories 2.0 | 0.892167 | -0.020936 |
| categories 3.5 | 0.917885 | +0.004782 |
| categories 4.0 | 0.922312 | +0.009209 |
| categories 4.5 | 0.924937 | +0.011834 |
| categories 5.0 | 0.925125 | +0.012022 |
| categories 6.0 | 0.925250 | **+0.012147** |
| features/details 3.0 | 0.917879 | +0.004776 |
| features/details 1.0 | 0.885755 | -0.027348 |

Raising `title` is sharply negative while raising `categories` is strongly
positive, which is the predicted asymmetry rather than generic weight
sensitivity. The gain plateaus across `4.5-6.0`.

## Full set (200 sessions), baseline `0.906193`

| Configuration | Score | Δ | HitRate | MRR | MTTC |
| --- | ---: | ---: | ---: | ---: | ---: |
| E28 baseline | 0.906193 | — | 0.995 | 0.789310 | 2.405 |
| max_n 3 | 0.908639 | +0.002446 | 0.995 | 0.797464 | 2.405 |
| categories 5.0 | 0.916931 | +0.010738 | 0.995 | 0.822437 | 2.365 |
| **categories 6.0** | **0.917406** | **+0.011213** | 0.995 | 0.823353 | 2.355 |
| categories 7.0 + max_n 3 | 0.915648 | +0.009455 | 0.995 | 0.817159 | 2.350 |
| categories 8.0 + max_n 3 | 0.915218 | +0.009025 | 0.995 | 0.815728 | 2.350 |
| categories 10.0 + max_n 3 | 0.915120 | +0.008927 | 0.995 | 0.816067 | 2.360 |
| categories 6.0 + max_n 3 | 0.916631 | +0.010438 | 0.995 | 0.820770 | 2.355 |
| categories 5.0 + features/details 3.0 + max_n 3 | 0.916104 | +0.009911 | 0.995 | 0.818347 | 2.345 |

Unlike E31, **every validation winner held on the full set.** The validation
plateau (`4.5-6.0`) and the full-set peak (`6.0`) agree.

The two changes do **not** compose: `categories 6.0` alone (`0.917406`) beats
`categories 6.0 + max_n 3` (`0.916631`). Once category matching dominates the
score, the extra phrase credit re-orders candidates the category weight had
already separated correctly.

## Scenario breakdown at `categories 6.0`

| Scenario | HitRate@10 | MRR (E28 -> E32) | MTTC (E28 -> E32) |
| --- | ---: | --- | --- |
| Buying | 0.9875 (unchanged) | 0.810774 -> **0.840000** | 1.8875 -> **1.8375** |
| Browsing | 1.0000 (unchanged) | 0.735417 -> **0.787827** | 2.3250 -> **2.2875** |
| Intent Override | 1.0000 (unchanged) | 0.805556 -> 0.805556 | 3.9000 -> 3.9000 |
| Boundary | 1.0000 (unchanged) | 1.000000 -> **0.911111** | 2.7000 -> **2.6000** |

No scenario loses a session. Browsing gains most (`+0.052410` MRR), which is
where E31 measured the largest remaining pool of loss.

**Boundary MRR regresses**, `1.000000 -> 0.911111`. Boundary is 10 sessions;
one target moved off rank 1. It is reported rather than smoothed over: the
pre-registered threshold is about HitRate@10, which is unchanged at `1.0000`,
and the same weight buys `+0.052410` MRR across the 80 Browsing sessions. A
10-session scenario cannot settle a weight on its own, but the direction should
be rechecked if Boundary is ever weighted more heavily.

## Decision

**Keep `categories = 6.0`.** New current best at `0.917406`.

**Reject `phrase_max_n > 2`**, retained at its no-op default. It is a real but
small standalone gain (`+0.002446`) that is negative in combination with the
change actually kept. `extract_phrases` and its tests stay so the measurement
is reproducible and the parameter is one edit away if the interaction changes.

Why the category weight worked, beyond the numbers: every prior ranking
experiment added a **new signal** — popularity, price, semantic similarity,
phrase adjacency, constraint completeness. This one adds nothing. It corrects
a mis-stated reliability ordering among signals already present. The customer
is known to quote the category path and is not known to quote the title, and
the weights said the opposite for twenty-eight experiments.

## Transfer risk

The mechanism depends on `initial_message` composing the opening line from the
target's category path. The private set is scored by the same evaluator code,
so the behaviour should transfer. It would not survive an organizer rewriting
the simulator to paraphrase category names heavily — the same exposure E19's
phrase bonus already carries, and smaller than E21's, whose gain reverses under
the coverage-stress diagnostic.

### Coverage-stress diagnostic

The stress catalog masks `title`, `features`, `description`, `price` and
`details` down to catalog-wide rates, but `categories` already has `1.00000`
coverage so it is left intact. Both weights were run on both catalogs:

| Catalog | E28 `categories 3.0` | E32 `categories 6.0` | E32 gain |
| --- | ---: | ---: | ---: |
| official | 0.906193 (hit 0.995) | 0.917406 (hit 0.995) | **+0.011213** |
| coverage stress | 0.875610 (hit **0.980**) | 0.896711 (hit **0.995**) | **+0.021101** |

**The gain is nearly twice as large under stress, and it recovers three
sessions of HitRate@10 that E28 loses there** (`0.980 -> 0.995`). This is the
opposite of E21, whose `+0.012194` official gain becomes `-0.020274` under the
same diagnostic, and it is what the mechanism predicts: when the fields the
customer only incidentally overlaps are stripped, the one field they are
guaranteed to quote carries more of the signal, so weighting it correctly
matters more, not less.

This is the strongest transfer evidence any retained layer in this project
carries. It does not remove the paraphrase exposure described above -- the
stress diagnostic attacks catalog sparsity, not simulator wording -- but it
rules out the failure mode that E21 exhibits.

## Reproduction

```powershell
python -m unittest discover -s tests          # 205 tests
python -m evaluator.local_evaluator           # TechnicalScore 0.917406
python -m scripts.build_coverage_stress_catalog
python -m scripts.run_dual_catalog_evaluation
```

Sweeps constructed the agent once per catalog and mutated
`reranker.FIELD_WEIGHTS` between runs; neither the FTS5 index nor the dense
index depends on the field weights.

## Limitations

- Only `categories`, `title`, `features`/`details` and `description` were
  swept. `store` (`1.5`) is untouched.
- Weights were swept one axis at a time around the E28 point, not jointly. A
  joint optimum may exist away from it.
- The plateau `4.5-6.0` is flat to within `0.0004` on validation. `6.0` is the
  peak on both splits, but any value in that band is defensible; the result
  should not be read as precision to one decimal place.
- Boundary MRR regression is unexplained beyond "one session of ten moved".
