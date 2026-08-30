# Rank-Margin Diagnostic and the Catalog-Quality Prior

## Status

Diagnostic, plus one rejected method. No change to the retained agent. The
result reorders what is worth doing next, so it is recorded here rather than
left in a conversation.

- Date: 2026-08-30
- Configuration measured: E13-C, `Agent(state_model="ledger", no_gain_probe=1)`,
  full public TechnicalScore `0.868714`
- Commands: `python -m scripts.trace_session`, plus per-turn candidate-pool
  inspection against the same FTS5 query the agent issues

## Why this diagnostic

E13-C reaches HitRate@10 `0.980`, so only four sessions are unfound. The
question is whether the remaining effort belongs to recall or to ranking.

| Lever | TechnicalScore now | If fully realised | Headroom |
| --- | ---: | ---: | ---: |
| Find the 4 missing sessions | 0.868714 | 0.878714 | **+0.010000** |
| Move every current hit to rank 1 | 0.868714 | 0.953200 | **+0.084486** |

Ranking headroom is **8.4x** recall headroom. Rank distribution over 200
sessions: 114 at rank 1, 30 at rank 2, 10 at rank 3, 42 at ranks 4-10, 4 missed.

## The four Buying misses

| Session | `rating_number` | Ever in the Top-100 pool | Best position in pool | Hard constraints |
| --- | ---: | --- | ---: | --- |
| `public_0020` | **1** | **never** | — | cotton, color: grey |
| `public_0054` | 132 | yes | 11 | fabric, Soft Fabric |
| `public_0161` | 202 | yes | 17 | cotton, cotton blend |
| `public_0179` | 217 | yes | 28 | spandex, 5% spandex |

One recall failure, three ranking failures.

`public_0020` is the documented cost of the popularity prior arriving. Its
target carries a single review against a target median of 6,846, and it never
enters the BM25 Top-100 at any turn. T15 named this risk explicitly; this is
the session where it lands.

The other three are in the pool the whole time and never crack the top ten.
All three plateau from turn 4: position frozen, term count frozen, the probe
asking openly but the intent card exhausted. All three share a shape -- every
hard constraint is a generic material word (`fabric`, `cotton`, `spandex`),
the least discriminative vocabulary available in a clothing catalog. The query
carries almost no separating power, so ranking falls back to field coverage
plus popularity, and targets with 132-217 reviews lose to pool members with
thousands.

## What decides rank 2

For the 40 sessions that hit at rank 2 or rank 3, the rerank score was
decomposed into its field-match and popularity components for the target and
for the item ahead of it.

| Why the rank-1 item is ahead | Sessions |
| --- | ---: |
| Better field match | 17 |
| Tied field match, won on popularity | 16 |
| Worse field match, won on popularity | 7 |

**23 of 40 are decided by popularity rather than by matching.**

| Score gap to rank 1 | Value |
| --- | ---: |
| Median | 0.669 |
| Minimum | 0.003 |
| Gaps below one field-weight unit | **23 / 40** |

Representative rows, where `m` is field match and `p` is the popularity term:

| Session | m target | p target | m winner | p winner | Gap |
| --- | ---: | ---: | ---: | ---: | ---: |
| `public_0048` | 7.00 | 9.87 | 8.00 | 8.87 | **0.003** |
| `public_0005` | 18.00 | 10.50 | 22.00 | 6.59 | 0.09 |
| `public_0022` | 26.00 | 11.82 | 28.00 | 9.92 | 0.10 |
| `public_0019` | 10.00 | 12.03 | 12.00 | 10.19 | 0.16 |

The pattern in the "better field match" group is consistent: the target has
markedly more reviews and slightly worse field coverage, and the two terms
almost exactly cancel. One additional field match is worth 1.0 to 4.0 points;
`1.2 * log1p(rating_number)` compresses an order-of-magnitude review
difference into roughly 1 to 2 points. The two signals sit on the same scale,
so the top of the list is a large near-tie region where the ordering is close
to arbitrary. That also explains why T15's weight sweep showed a broad plateau
from 0.8 to 1.8 rather than a peak.

## Rejected: a catalog-quality prior

`average_rating` has full catalog coverage and appears in no scored path. It
was the last unused catalog field with complete coverage, which is the same
description `rating_number` had before T15.

| Field | Catalog median | Target median | Target median's catalog percentile |
| --- | ---: | ---: | ---: |
| `rating_number` | 12 | 6,846 | **0.995** |
| `average_rating` | 4.200 | 4.400 | 0.668 |

The distribution is asymmetric in a way the median hides: only **16/200**
targets rate below 4.0, against **32.6%** of the catalog, while 87/200 rate at
or above 4.5 against 33.2% of the catalog. Poorly rated items are four times
under-represented among targets; well rated items are only mildly
over-represented. The signal is real but far weaker than popularity's.

Sweep of `quality_weight * average_rating` added to the rerank score, on the
same seed and split as every other sweep in this project:

| `quality_weight` | Development | **Validation** | Full |
| ---: | ---: | ---: | ---: |
| 0.0 (off) | 0.869605 | **0.867378** | 0.868714 |
| 0.5 | 0.871446 | 0.865258 | 0.868971 |
| 1.0 | **0.872918** | 0.867326 | **0.870681** |
| 2.0 | 0.866353 | **0.868299** | 0.867132 |

**Reject.** Validation spans `0.003` across the whole sweep, is non-monotone,
and shows no plateau. Development and validation disagree outright:
development peaks at `1.0`, validation peaks at `2.0`, and at validation's
argmax development is at its worst value. T15's popularity sweep is the
contrast -- development and validation peaked at `1.2` independently, on a
plateau. Nothing of that shape is present here. The code was removed.

## What this means for sequencing

The near-ties at the top of the list are **not breakable by catalog metadata**.
`average_rating` was the last unused fully-covered field, and it carries
nothing usable. Two fields already in the score are cancelling each other
inside a margin of 0.669, and no third catalog signal is available to arbitrate.

That constrains what can work next:

- **E12 MiniLM + RRF, as currently gated, addresses the smaller lever.** Its
  Gate 1 measures first-turn Recall@100. Recall limits exactly one of 200
  sessions. Worse, Recall@100 is structurally incapable of detecting the
  difference between rank 2 and rank 1, which is where 89% of the remaining
  headroom sits. If E12 is run, Gate 1 should be restated to measure rank
  quality -- for instance MRR of the fused list over the 196 found sessions --
  or it will pass or fail for reasons unrelated to the score.
- **The remaining lever is semantic discrimination among candidates that all
  satisfy the stated constraints.** That is the cross-encoder or learned-fusion
  work the E12 design explicitly defers to "the next experiment". On this
  evidence that experiment, not E12 itself, is the one worth designing.
- **IDF deserves one re-measurement, with the reasoning stated in advance.**
  The three ranking misses have queries made entirely of generic material
  words, which is the textbook case for IDF. E8 and E10 rejected it, but E8 ran
  in the contaminated-gazetteer era and T14 later showed IDF was a *substitute*
  for that contamination rather than an increment. The conditions have changed:
  clean gazetteer, ledger state, probe. This is a hypothesis, not a prediction.
  Stage 0 is the standing warning against acting on "obviously correct"
  reasoning in this pipeline without measuring.

## Limitations

- 40 sessions in the rank-2/3 decomposition, and 4 in the miss analysis.
- The score decomposition uses the turn at which the session hit. Earlier turns
  have different term sets and would decompose differently.
- The quality-prior sweep tested four weights with a linear term. A different
  functional form -- a penalty below a rating threshold, matching the observed
  asymmetry -- was not tested and is not ruled out by this result.
