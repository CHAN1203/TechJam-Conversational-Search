# Conversation State Experiment v1

## Hypothesis

The field reranker can only use constraints present in the current query.
Maintaining active constraints across turns and asking one targeted attribute
per turn should expose more relevant catalog terms and produce earlier hits.

## Method

- Preserve the field reranker v1 and its 100-candidate pool unchanged.
- Accumulate unique constraint terms within each session.
- Ignore explicit no-preference replies instead of indexing their wording.
- Clear prior terms when the user explicitly overrides the earlier intent.
- Prioritize clarification attributes from anonymized profile tags, then use a
  fixed non-repeating fallback order.
- Return both one clarification question and Top-10 recommendations every turn.

The agent uses only the catalog, anonymized profile, and messages disclosed to
it through the official interface. It does not read `public_set.jsonl`, hidden
intent cards, behavior controls, ground-truth identifiers, or evaluator code.

## Public-set result

| Variant | HitRate@10 | MRR | MTTC | TechnicalScore |
| --- | ---: | ---: | ---: | ---: |
| BM25 baseline | 0.125 | 0.068034 | 9.81 | 0.106710 |
| Field reranker v1 | 0.160 | 0.076750 | 9.46 | 0.133825 |
| Conversation state v1 | **0.870** | **0.533748** | **4.565** | **0.723824** |

| Scenario | Reranker HitRate@10 | Conversation HitRate@10 |
| --- | ---: | ---: |
| Buying | 0.2375 | **0.8875** |
| Browsing | 0.0875 | **0.9625** |
| Intent Override | 0.133333 | **0.533333** |
| Boundary | 0.2000 | **1.0000** |

The 174 successful sessions first hit on these turns:

| Turn | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Hits | 28 | 40 | 25 | 32 | 31 | 1 | 5 | 12 |

## Interpretation and limitations

The result confirms that conversation policy, not only retrieval, is a major
bottleneck. Targeted questions legally expose additional requirements through
the Agent interface, and persistent state makes those answers searchable.

This is still a public-set result. The attribute policy is heuristic and not
yet derived from candidate entropy, so private-set performance may differ.
The next experiment should compare profile-driven ordering with fixed ordering
and candidate-grounded attribute selection while keeping retrieval fixed.
