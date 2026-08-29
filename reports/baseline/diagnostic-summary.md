# Baseline Diagnostic Summary

## Scope

These diagnostics use the frozen 50,000-product catalog, all 200 public
sessions, and the unmodified official BM25 starter. They do not modify the
evaluator or public labels.

## First-turn BM25 candidate recall

Candidate recall answers whether the hidden target appears anywhere within a
larger first-turn BM25 candidate list. It is not the competition HitRate@10:
the official evaluator permits up to 10 turns, and Intent Override sessions
cannot convert before the replacement intent arrives on turn 3 or 4.

| Scenario | Sessions | Recall@10 | Recall@50 | Recall@100 | Recall@500 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Overall | 200 | 0.185 | 0.38 | 0.525 | 0.86 |
| Buying | 80 | 0.2375 | 0.475 | 0.5875 | 0.9375 |
| Browsing | 80 | 0.025 | 0.1875 | 0.3625 | 0.7625 |
| Intent Override | 30 | 0.533333 | 0.666667 | 0.833333 | 0.966667 |
| Boundary | 10 | 0.0 | 0.3 | 0.4 | 0.7 |

The overall target count grows from 37 in the Top-10 to 172 in the Top-500.
For Browsing it grows from 2 to 61 targets. BM25 therefore retrieves many
useful candidates but ranks them poorly for vague requests. Dense retrieval is
still relevant because 28 targets overall, including 19 Browsing targets, are
absent from BM25's Top-500.

## Catalog field coverage

| Field | Present | Missing | Coverage |
| --- | ---: | ---: | ---: |
| title | 49,998 | 2 | 0.99996 |
| categories | 50,000 | 0 | 1.0 |
| details | 48,330 | 1,670 | 0.9666 |
| features | 44,781 | 5,219 | 0.89562 |
| store | 49,686 | 314 | 0.99372 |
| description | 26,113 | 23,887 | 0.52226 |
| price | 10,527 | 39,473 | 0.21054 |
| average_rating | 50,000 | 0 | 1.0 |
| rating_number | 50,000 | 0 | 1.0 |

`details`, `features`, `categories`, and `title` are sufficiently populated to
ground candidate attributes and later clarification questions. `description`
is supplemental. `price` is too sparse to drive a default budget question or a
global hard filter without explicit missing-value behavior.

## Next implementation recommendation

Prioritize a lightweight local reranking experiment over BM25's Top-500 before
adding dense retrieval. The 67.5-point gap between overall Recall@10 and
Recall@500 is larger than the 14-point gap beyond Top-500, so ranking is the
dominant measured bottleneck. Dense retrieval should follow as the second
experiment to recover the 28 targets BM25 still misses, especially the 19
Browsing targets.

Clarification entropy should initially use grounded values derived from
`details`, `features`, and `categories`. Budget should be considered only when
the current candidate set has adequate price coverage, with `other` retained as
the safe fallback.
