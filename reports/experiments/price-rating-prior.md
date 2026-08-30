# Price and Rating Priors

Date: 2026-08-30 (re-measured on the merged E19 stack the same day)
Status: **E21, current best.** On the merged stack, TechnicalScore
`0.868476` -> `0.880670`. Rating prior implemented, swept, and shipped
disabled at `0.0`.

The sweeps in "Weight selection" below were run on the **pre-merge E11
stack**, before E13-E20 existed locally, and are kept because they are the
evidence the prior was designed from. The post-merge re-sweep that decides
the shipped weight is in "Re-sweep on the merged stack" at the end.

## Where it came from

The popularity prior fixed ties by asking "which of these does anyone buy?"
Two more fields on every catalog row answer adjacent questions and were still
unused: `price` and `average_rating`. Both were measured against the targets
before either was weighted.

## The measurement

Over the full 50,000-product catalog and all 200 public targets:

| | Catalog | Targets |
| --- | ---: | ---: |
| Carries a price | 21.1% | **89.0%** |
| Mean `average_rating` | 4.087 | **4.372** |

Price is the stronger of the two, and the gap is not just popularity in
disguise. Restricted to the catalog's top popularity decile — where 173 of the
200 targets already sit — only **31.6%** of products carry a price, while the
targets in that same decile are still **89.0%** priced.

The rating gap does not survive the same control. Inside the top decile the
target mean is `4.385` against a catalog mean of `4.301`, most of the original
0.285 difference having been popularity all along. There is also little range
to work with: 67.4% of rated products fall between 4.0 and 5.0 stars.

The reading is that a priced listing is an *active* listing, and only active
listings get purchased. That is a fact about how the dataset was built, not a
claim that shoppers prefer cheap or expensive items — only presence is used,
never the value.

## Implementation

`rerank_candidates` adds `price_weight * has_price` and
`rating_weight * average_rating` alongside the popularity term. `has_price` is
a flat 0/1 bonus on presence; the price value itself is never read. Both
fields are collected into their own dicts during index construction, like
`rating_number` before them, so the FTS5 `bm25()` column weights stay
untouched. A missing or malformed value contributes zero, which for the rating
term means an unrated item is scored as unrated rather than as average.

Price is a bonus and never a filter: 11% of targets carry no price, so
excluding unpriced candidates would make those sessions unwinnable.

## Weight selection

Both swept on the stratified split and seed used throughout
(`techjam-clarification-v1`, 80 validation sessions), with popularity held at
`1.2`. Each prior was swept **independently against the popularity-only
baseline** — the two were never swept jointly.

Price, with rating at `0.0`:

| Weight | Validation | Development | Full | HitRate@10 | MRR | Boundary |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.0 | 0.844722 | 0.839915 | 0.841838 | 0.965 | 0.662125 | 0.9000 |
| 1.0 | 0.854561 | 0.845770 | 0.849286 | 0.970 | 0.672954 | 0.9000 |
| **2.0** | 0.868357 | **0.852087** | **0.858595** | **0.975** | 0.692982 | 0.9000 |
| 3.0 | **0.872202** | 0.847927 | 0.857637 | 0.970 | **0.702456** | 0.9000 |
| 5.0 | 0.869442 | 0.846047 | 0.855405 | 0.970 | 0.693018 | 0.9000 |

Rating, with price at `0.0`:

| Weight | Validation | Development | Full | HitRate@10 | MRR | Boundary |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.0 | 0.844722 | 0.839915 | 0.841838 | 0.965 | 0.662125 | 0.9000 |
| 0.5 | 0.867659 | **0.854514** | **0.859772** | **0.975** | 0.697907 | 0.9000 |
| 1.0 | 0.868015 | 0.849611 | 0.856973 | 0.970 | 0.699575 | 0.9000 |
| 2.0 | 0.872853 | 0.846861 | 0.857258 | 0.970 | 0.700526 | 0.9000 |
| 4.0 | **0.873244** | 0.839974 | 0.853282 | 0.965 | 0.696274 | 0.9000 |

Price ships at `2.0`, which is a deliberate departure from the
validation-only rule the popularity prior followed. Validation alone favours
`3.0` by `0.0039`, but development and full both peak at `2.0`, and validation
is flat from `2.0` to `5.0` within `0.004` — a plateau, not a peak. `2.0` is
the point where all three splits agree; `3.0` wins on the split with 80
sessions while losing on the other 120.

Reproduce with:

    python -m scripts.run_popularity_sweep --weights 1.2 --price-weight 2.0
    python -m scripts.run_popularity_sweep --weights 1.2 --rating-weight 0.5

## Why the rating prior ships at zero

Read on its own the rating table looks like a win — `0.5` gains `+0.0179` full
over baseline, nearly matching price at `2.0`. It is not shipped, for two
reasons.

The measurement says most of that signal is popularity re-entering through a
second door: once popularity is controlled for, the target/catalog rating gap
narrows from `0.285` to `0.084`. A prior that mostly re-weights what
`popularity_weight` already captures adds a tuned parameter without adding
information, and every extra parameter tuned on 200 sessions is another chance
to fit noise.

The sweep shape agrees. Development peaks at `0.5` and then falls monotonically
while validation keeps climbing to `4.0` — the two splits disagree about the
direction, which is what overfitting looks like. Price does not do this.

The code path is implemented and unit-tested so the weight can be turned on
from a single constant if the private set justifies it, but the default is
`0.0` and nothing in the current results justifies more.

## Result (pre-merge E11 stack)

Popularity `1.2` alone versus popularity `1.2` + price `2.0`, full 200:

| Metric | Popularity only | + Price |
| --- | ---: | ---: |
| HitRate@10 | 0.965 | **0.975** |
| MRR | 0.662125 | **0.692982** |
| MTTC | 2.965 | **2.840** |
| TechnicalScore | 0.841838 | **0.858595** |

| Scenario | Popularity only | + Price |
| --- | ---: | ---: |
| Buying | 0.9500 | **0.9750** |
| Browsing | 1.0000 | 1.0000 |
| Intent Override | 0.933333 | 0.933333 |
| Boundary | 0.9000 | 0.9000 |

The entire gain lands in Buying, which is the scenario the prior was reasoned
about: an active, purchasable listing matters most when the user is actually
buying. Nothing regressed.

## Re-sweep on the merged stack (E21)

E13-E20 landed from a parallel branch after these sweeps were run, so the
weight was re-swept rather than carried over. Same split and seed, on top of
E19 (routing + semantic reranking + phrase bonus):

| Price weight | Validation | Full | HitRate@10 | MRR |
| ---: | ---: | ---: | ---: | ---: |
| 0.0 (E19) | 0.883582 | 0.868476 | 0.980 | 0.715919 |
| 1.0 | 0.892926 | 0.873253 | 0.980 | 0.728177 |
| **2.0** | **0.895201** | **0.880670** | 0.980 | **0.756899** |
| 3.0 | 0.894515 | 0.878848 | 0.980 | 0.749825 |
| 5.0 | 0.892311 | 0.871899 | 0.975 | 0.736331 |

`2.0` holds, and the split disagreement noted above is gone: validation and
full now peak at the same weight. The deviation from the validation-only
rule that `2.0` originally required no longer applies on this stack.

No scenario hit rate moves (Buying `0.9875`, Browsing `1.0000`, Intent
Override `0.933333`, Boundary `0.9000`) and MTTC is `0.005` worse; the whole
`+0.012194` is MRR `+0.040980`. That is the expected shape for a
tie-breaking prior stacked under E19: the phrase bonus decides which
candidates surface, the price prior orders the ones that surface tied.

## Limitations

- **E21 has not been run through the coverage-stress diagnostic.** T25's
  stress catalog masks price down to 42 of 200 targets by construction, so
  this is the layer most exposed to it. The dual-catalog tooling supports
  it directly: `python -m scripts.run_popularity_sweep --weights 1.2
  --price-weight 2.0`.
- **Price and rating were never swept jointly.** Both tables above hold the
  other weight at zero, so the shipped combination is the price column, not a
  jointly optimised pair. If the rating prior is ever enabled its weight must
  be re-swept on top of price `2.0`, not read off the table here.
- `has_price` is presence only. Whether the price *value* carries signal —
  targets clustering in a band, or matching a budget the user disclosed — is
  untested. Budget constraints in conversation are currently handled by the
  slot extractor, not the ranker.
- Boundary sits at `0.9000` across every weight of both priors, as it did
  across the entire popularity sweep. Those 9 of 10 sessions are limited by
  something no ranking prior has moved.
- Both weights are tuned on 200 public sessions. Price is the safer of the two
  to carry into the private set because its measurement survives the
  popularity control and its two splits agree; that is the reason for the
  asymmetry in what ships.
