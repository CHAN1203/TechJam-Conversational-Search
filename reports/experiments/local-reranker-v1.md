# Local Reranker Experiment v1

## Hypothesis

BM25 retrieves many hidden targets within its first 100 candidates but ranks
them outside the scored Top 10. A deterministic field-aware reranker should
improve Top-10 ranking without a network dependency.

## Method

- Retrieve the first 100 BM25 candidates.
- Score each query term once at its highest-value matching field.
- Use field weights: title `4.0`, categories `3.0`, features/details `2.0`,
  store `1.5`, and description `1.0`.
- Preserve BM25 order when field-aware scores tie.
- Return the first 10 reranked identifiers through the unchanged Agent API.

## Public-set result

| Variant | HitRate@10 | MRR | MTTC | TechnicalScore | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| BM25 baseline | 0.125 | 0.068034 | 9.81 | 0.106710 | Reference |
| Field reranker v1 | **0.160** | **0.076750** | **9.46** | **0.133825** | Keep |
| v1 + BM25 rank prior | 0.155 | 0.073992 | 9.51 | 0.129498 | Reject |

The kept variant adds 12 hits and loses 5 baseline hits, for a net gain of 7
sessions. HitRate@10 improves by 28.0%, and TechnicalScore improves by 25.4%.

| Scenario | Baseline HitRate@10 | Reranker HitRate@10 |
| --- | ---: | ---: |
| Buying | 0.2375 | 0.2375 |
| Browsing | 0.0250 | 0.0875 |
| Intent Override | 0.133333 | 0.133333 |
| Boundary | 0.0000 | 0.2000 |

## Interpretation

The result supports the ranking-bottleneck diagnosis: field coverage over a
larger lexical candidate pool improves vague Browsing and Boundary sessions
without reducing aggregate Buying or Intent Override hit rate. Adding an
explicit BM25 rank prior reduced every core aggregate metric relative to v1,
so it is not retained.

This is a public-set experiment, not evidence of private-set generalization.
The next experiment should add conversational constraint state and grounded
clarification while keeping this reranker fixed.
