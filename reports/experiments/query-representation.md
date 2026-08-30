# E29 / E30: Query Representation — Semantic Projection and Hard/Soft Constraints

## Status

**Both rejected.** The interesting part is not that they failed but why, because
between them they bound how much a "query understanding" module can be worth in
this system at all.

- Date: 2026-08-30
- Baseline: the merged agent, `Agent(catalog_path)`, TechnicalScore `0.906943`
- Branch: `experiment/semantic-query-projection`

## What already existed

The agent constructs **four** query representations per turn, without anyone
having designed them as a module:

| # | Representation | Feeds |
| --- | --- | --- |
| 1 | `slots_view()` -> `required_terms` | the completeness bonus (structured) |
| 2 | `" OR ".join(terms)` | the FTS5 lexical retrieval |
| 3 | `" ".join(terms)` | the dense index (semantic scoring) |
| 4 | `extract_bigrams(user_message)` | the phrase bonus |

Structured and semantic are therefore already separated and already used
differently. What was missing was any *rewriting*: representation 3 is the same
bag of words as representation 2, joined by spaces rather than `OR`.

## E29: slot-projected semantic query (rejected)

The dense index was being handed the raw accumulated bag, evaluator phrasing
included. Projecting only the classified, still-active constraints, ordered the
way a product title reads, produces a visibly cleaner query:

```
terms:  tees blouses tunics hand wash only what matters polyester 60
slots:  blouses tees tunics polyester
```

| Configuration | TechnicalScore | Δ |
| --- | ---: | ---: |
| `semantic_query="terms"` (current) | 0.906943 | — |
| `semantic_query="slots"` | 0.906993 | **+0.000050** |

**The cleaner query is worth essentially nothing, and it cannot be worth much.**
Turning the semantic term off entirely costs `0.001871`. That is the whole
budget any change to `query_text` is competing for, because `query_text` feeds
only `semantic_scores`, the smallest of the reranker's terms. The projection
captured 2.7% of it.

This bound does not depend on how good the representation is. An LLM producing
`"leather running shoes suitable for gym, minimal style"` would still be
competing for `0.001871`, while costing a model dependency, token spend,
latency, and the project's current `usage: {prompt_tokens: 0}` property. On
this evidence LLM-assisted query rewriting is not worth building here.

## E30: hard/soft constraint separation (rejected)

### The hard/soft labels are observable, exactly

The intent card's `hard_constraints` / `soft_preferences` split is hidden, but
the evaluator's phrasing gives it away. Measured over all 200 public sessions,
matching every disclosed constraint against its hidden label:

| Observable signal | hard | soft | hard share |
| --- | ---: | ---: | ---: |
| turn 1, `"A key requirement is:"` | 80 | 0 | **100%** |
| override, `"What I need is:"` | 30 | 0 | **100%** |
| turn 1, no marker | 0 | 30 | **0%** |
| reply, `"For that, what matters is:"` | 198 | 99 | 66.7% |
| *(overall base rate)* | 308 | 129 | 70.5% |

Two phrases identify a hard constraint with zero errors across 110 occurrences.
This is reading the simulator's templates, not understanding language, and it
is the mirror image of E25: there, catalog IDF gave its highest weight to
`matters`, `requirement` and `key` precisely because they are template residue.

It also disposes of a question two experiments had already answered
indirectly. `source` (volunteered vs answered) is a poor proxy for hard/soft:
turn-1 volunteered constraints are 73% hard, answered ones 66.7% hard --
barely different from the 70.5% base rate. That is why E24-C1's
`answered_weight` and E23's `recency_weight` both swept to zero. **They were
proxies for a distinction that the signal they used does not carry.**

### The result

| Configuration | TechnicalScore | MRR | Δ |
| --- | ---: | ---: | ---: |
| off (current) | 0.906943 | 0.791810 | — |
| `constraint_strength=True` | 0.904602 | 0.784006 | **-0.002341** |

HitRate@10 and every scenario are unchanged; the loss is entirely MRR.

### Why narrowing the requirement makes it worse

The completeness bonus rewards a candidate that matches *every* currently-known
constraint. Its value comes from being hard to earn.

| | `required_terms` per turn | Candidates of 100 earning the bonus |
| --- | ---: | ---: |
| off | 1.76 | 60.0 |
| hard/soft on | 1.36 | **64.8** |

Requiring only the hard constraints makes the bonus *easier* to earn, so it
separates less. We widened the holes in a sieve. The direction is wrong, not
the magnitude.

E22 is the confirming counter-example: applying the same bonus to Browsing
sessions as well was worth `+0.004071`. That change **widens where the bonus
applies while keeping it equally strict**. This one relaxes strictness. The two
results together say the bonus should be extended, never loosened.

## E30-A: the opposite construction (also rejected)

E30's limitation section named the natural follow-up: keep `required_terms` as
it is and add a *separate* bonus for satisfying all hard constraints. Stricter,
not looser. It was implemented and measured.

| Configuration | TechnicalScore |
| --- | ---: |
| off | 0.906943 |
| `hard_bonus=2.0` | 0.906943 |

Identical to every digit -- and for the opposite reason to E30.

| | Terms in the test | Candidates of 100 satisfying it |
| --- | ---: | ---: |
| E30, hard replaces required | 1.36 | 64.8 |
| current, required | 1.76 | 60.0 |
| E30-A, all hard terms | 6.98 | **0.1** |

`hard_surfaces()` marks every token of a message that carried a hard marker,
including the `I'm looking for {category}` clause, so the hard set runs 5.22
terms wider than `required_terms`. Demanding a candidate match all of them is
satisfied by roughly one candidate in a thousand. The bonus went to nobody, so
nothing reordered.

The two failures bracket the mechanism:

```
E30    1.36 terms  ->  64.8 / 100 earn it  ->  -0.002341   sieve too coarse
now    1.76 terms  ->  60.0 / 100 earn it  ->   baseline
E30-A  6.98 terms  ->   0.1 / 100 earn it  ->   0.000000   sieve too fine
```

The completeness bonus sits on a sweet spot: few enough candidates must earn it
for it to discriminate, but not so few that nobody does. Both sides of that
spot were tested and both are worse. It also explains why E22 worked where
these did not -- extending the bonus to Browsing changes *where* it applies
without touching how hard it is to earn, which is the only direction that
leaves the sweet spot intact.

## Graceful degradation

`constraint_strength` was built so that an unmarked conversation is
indistinguishable from today's behaviour: nothing is labelled `HARD`, the hard
set is empty, and `required_terms` is left exactly as computed. A private
simulator phrasing requirements differently, or a real shopper, would simply
fall back. That property is real and was verified -- it is just not what
decided the experiment, because the mechanism is wrong even when detection
works perfectly.

## Nothing was retained

All three switches were removed, along with the ledger's `strength` field, the
marker detection and `hard_surfaces()`. `starter/agent.py` and
`starter/ledger.py` are byte-identical to the branch point.

Keeping the detection was considered, on the argument that `strength` is data
rather than behaviour, like the existing `source` field. It was rejected on the
T3 precedent -- reject the method, remove the code -- because that precedent is
what makes this ledger trustworthy, and `source` is a documented part of the
ledger's design while `strength` would have been the residue of a failed
experiment with no caller. Nothing had ever read `hard_surfaces()`.

The finding survives regardless: the marker table above is the product, not the
six lines that implemented it. Anything that later needs a hard/soft
distinction can reconstruct them from this report.

## What this bounds

Adding a query-understanding module to this system is bounded above by what the
consumers of those queries are worth:

| Consumer | Marginal value | Ceiling for improving its input |
| --- | ---: | --- |
| Semantic scoring | 0.001871 | any rewrite, LLM or not |
| Completeness bonus | 0.009154 | any structured refinement |
| Lexical retrieval | — | E20 showed changing it costs sessions |

Neither half is large, and the structured half now has a measured direction
that is the opposite of the proposed one. This is not evidence that query
understanding is worthless in general; it is evidence that in a system whose
performance is dominated by a popularity prior worth `0.060`, it is not where
the remaining headroom lives.

## Limitations

- 200 public sessions, and the hard/soft signal is simulator phrasing that a
  differently-worded private set would not carry.
- E29 tested one projection: slot-ordered, active-only. Other orderings, or
  including unslotted terms, were not tried.
- E30 tested narrowing the requirement. The opposite construction -- keep
  `required_terms` as is and add a *separate* bonus for satisfying all hard
  constraints -- is untested and is the natural follow-up.
