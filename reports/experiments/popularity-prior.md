# Popularity Prior

Date: 2026-08-29
Status: current best. TechnicalScore `0.747917` -> `0.841838`.

## Where it came from

A failed Intent Override session. Every one of the ten returned products
satisfied every disclosed constraint — leather, buckle, belt — so nothing was
left to separate them and ties fell back to BM25 order.

    target   B071X54486  Hide & Drink Full Grain Leather Men's Belt   6614 ratings
    rank 1   B073FC5MJH  ITIEZY Men's Genuine Leather Ratchet Belt      21 ratings
    rank 3   B07MB6TNJ8  Savile Row Top Grain Leather Reversible Belt   18 ratings
    rank 5   B013RTTUC4  Landfilldzine Recycled Irrigation Hose Belt    10 ratings

The retrieval was correct. The ranking had no way to prefer the item a real
customer would actually buy.

## The measurement

The hidden target is a real purchase record, and purchased items are reviewed
items.

| | Catalog | Targets |
| --- | ---: | ---: |
| Median `rating_number` | 12 | **6,846** |

The median target sits at the **99.5th percentile** of catalog popularity.
193 of 200 targets fall in the top quartile, 173 in the top decile, and only 2
in the bottom quartile. The field has 100% coverage and was previously unused.

## Guard against a bestseller list

A prior this strong risks degenerating into "always recommend popular items".
Measured directly: an agent that ignores the conversation entirely and returns
the globally most-reviewed products every turn scores **HitRate@10 0.035**
(7 of 200).

Retrieval narrows 50,000 products to a few hundred plausible ones; popularity
orders that set. The two are complementary. Popularity is not substituting for
conversational understanding.

## Implementation

`rerank_candidates` adds `popularity_weight * log1p(rating_number)` to the
field-match score. `rating_number` is collected into a separate dict during
index construction rather than added to the FTS5 table, so the `bm25()` column
weights are untouched. A missing or malformed value contributes zero.

## Weight selection

Swept on the same stratified split and seed the clarification ablation used
(`techjam-clarification-v1`, 80 validation sessions). The winner was chosen on
validation only.

| Weight | Validation | Development | Full | Boundary |
| ---: | ---: | ---: | ---: | ---: |
| 0.0 | 0.771539 | 0.732169 | 0.747917 | 0.9000 |
| 0.15 | 0.803201 | 0.772629 | 0.784858 | 0.9000 |
| 0.3 | 0.826132 | 0.786288 | 0.802226 | 0.9000 |
| 0.5 | 0.830092 | 0.810395 | 0.818274 | 0.9000 |
| 0.8 | 0.837653 | 0.824992 | 0.830057 | 0.9000 |
| **1.2** | **0.844722** | **0.839915** | **0.841838** | 0.9000 |
| 1.8 | 0.838857 | 0.828661 | 0.832739 | 0.9000 |
| 2.5 | 0.821893 | 0.821475 | 0.821642 | 0.9000 |
| 4.0 | 0.813613 | 0.803594 | 0.807601 | 0.9000 |
| 8.0 | 0.773765 | 0.777014 | 0.775714 | **0.8000** |
| 16.0 | 0.755640 | 0.749870 | 0.752178 | **0.8000** |

Development and validation peak at `1.2` independently, and 0.8 to 1.8 is a
plateau rather than a spike. At weights of 8 and above Boundary drops from
`0.9000` to `0.8000`: the failure mode where popularity overwhelms constraint
matching is real, but appears only well past the peak.

Reproduce with:

    python -m scripts.run_popularity_sweep

## Result

| Metric | E9 | E11 |
| --- | ---: | ---: |
| HitRate@10 | 0.895 | **0.965** |
| MRR | 0.549056 | **0.662125** |
| MTTC | 4.215 | **2.965** |
| TechnicalScore | 0.747917 | **0.841838** |

| Scenario | E9 | E11 |
| --- | ---: | ---: |
| Buying | 0.8750 | **0.9500** |
| Browsing | 0.9625 | **1.0000** |
| Intent Override | 0.766667 | **0.933333** |
| Boundary | 0.9000 | 0.9000 |

Every scenario improved or held, and MTTC fell by 1.25 turns.

## Limitations

- The weight is tuned on 200 public sessions. If the private set draws targets
  with a different popularity profile the optimum moves. `1.2` was chosen
  because it sits mid-plateau, not because it is the argmax.
- This is a prior about **how the dataset was constructed** — targets are real
  purchase records, and purchases concentrate on popular items. It is not
  personalization and should not be described as such in the report. The
  anonymized `user_profile` is still used only for clarification ordering.
- Boundary is unchanged at `0.9000` across every weight tested. Those 9 of 10
  sessions are limited by something else.
