# Adaptive Intent-Aware Retrieval Design

## Goal

Build a reproducible, offline-first Track 4 agent that improves the official
TechnicalScore by maintaining structured conversational constraints, routing
between lexical and semantic retrieval, ranking candidates, and asking a
grounded clarification question while still recommending products every turn.

## Verified Starting Point

The repository is based directly on the official participant starter at commit
`3407835`. The unmodified starter was evaluated on all 200 public sessions with
Python 3.12.10 and the official 50,000-product catalog.

| Metric | Verified value |
| --- | ---: |
| HitRate@10 | 0.125 |
| MRR | 0.068034 |
| MTTC | 9.81 |
| Efficiency | 0.119 |
| TechnicalScore | 0.10671 |

Scenario results show that the first bottleneck is recall for vague intent:

| Scenario | Sessions | HitRate@10 | MRR | MTTC |
| --- | ---: | ---: | ---: | ---: |
| Buying | 80 | 0.2375 | 0.126508 | 8.625 |
| Browsing | 80 | 0.025 | 0.004514 | 10.75 |
| Intent Override | 30 | 0.133333 | 0.104167 | 10.066667 |
| Boundary | 10 | 0.0 | 0.0 | 11.0 |

## Product Thesis

A shopping agent should not use one fixed search strategy. It should maintain
a structured belief over active and revoked user constraints, dynamically
combine lexical and semantic retrieval, and ask the available question with
the highest expected value for reducing product uncertainty.

## Constraints

- Preserve the official `Agent.reset` and `Agent.respond` interfaces.
- Never modify `evaluator/` or public labels when reporting scores.
- Return at most 10 valid, unique catalog `parent_asin` values in ranked order.
- Support all four scenarios within the 10-turn session limit.
- Keep the catalog read-only and retrieval in memory.
- Keep the scored path functional without network access or live credentials.
- Treat external LLM calls as optional experiments with an offline fallback.
- Record latency, token usage, model choice, and estimated cost.
- Do not build a competition UI; the official headless evaluator is the product
  interface for this track.

## Architecture

### Offline preparation

1. Normalize searchable product fields without changing catalog records.
2. Build the existing SQLite FTS5 lexical index.
3. Build a compact local embedding index for semantic retrieval.
4. Derive candidate-grounded attribute statistics for clarification.
5. Persist only reproducible derived assets that the submission can rebuild.

### Runtime turn

1. Convert the latest user message into a constraint-state delta.
2. Update a per-session constraint ledger containing value, attribute, strength,
   status, and source turn.
3. Classify the current state as Buying, Browsing, or Override-aware and choose
   retrieval weights.
4. Build both a structured lexical query and a semantic query.
5. Retrieve lexical and semantic candidate lists independently.
6. Fuse candidates with Reciprocal Rank Fusion before experimenting with learned
   or calibrated score weighting.
7. Rerank a bounded candidate set with a lightweight local cross-encoder.
8. Select one candidate-grounded `ask_attribute`; use `other` only as a safe
   fallback when no specific undisclosed attribute is useful.
9. Return both the question and Top-10 recommendations on every turn.

## Component Boundaries

- `starter/agent.py`: official adapter and orchestration only.
- `src/catalog.py`: catalog loading and normalized product representation.
- `src/state.py`: session constraint ledger and state transitions.
- `src/query.py`: lexical and semantic query construction.
- `src/retrieval.py`: sparse and dense candidate retrieval.
- `src/fusion.py`: RRF and later intent-aware fusion policies.
- `src/reranking.py`: bounded local reranking with deterministic fallback.
- `src/clarification.py`: candidate-grounded question-value policy.
- `src/telemetry.py`: latency, token, and experiment measurements.
- `scripts/analyze_public_set.py`: read-only dataset and baseline diagnostics.
- `scripts/run_experiment.py`: reproducible evaluator wrapper and result ledger.

These boundaries are targets, not permission to create unused abstractions.
Each module is introduced only when its first tested behavior is implemented.

## Experiment Order

1. Measure BM25 candidate recall at 10, 50, 100, and 500.
2. Compare BM25, dense retrieval, and fixed RRF hybrid retrieval.
3. Hold retrieval fixed and compare fusion ranking with local cross-encoder
   reranking.
4. Add the constraint ledger and verify accumulation, revocation, and override.
5. Compare fixed, entropy-based, and expected-value clarification policies.
6. Compare fixed hybrid fusion with Buying/Browsing-aware routing.
7. Attempt LLM query decomposition or listwise reranking only after the offline
   pipeline is stable and only as measured optional experiments.

Every experiment must report overall and per-scenario metrics. A component is
kept only when it improves its target metric without an unacceptable regression
in another core metric, latency, memory, or reproducibility.

## Testing Strategy

- Contract tests for valid `respond` output and reset-before-respond behavior.
- Unit tests for state accumulation, replacement, revocation, and boundary input.
- Retrieval tests against small deterministic catalogs.
- Ranking tests that preserve unique valid identifiers and deterministic order.
- Clarification tests preventing repeated or ungrounded attributes.
- End-to-end execution with the unmodified official evaluator.
- A no-network execution check for the final scored path.

All behavior changes follow red-green-refactor: introduce a failing test, confirm
the expected failure, implement the smallest passing behavior, and rerun the
complete test suite.

## Delivery Evidence

- Reproducible baseline and experiment results.
- An ablation table showing the contribution of retrieval, reranking, state,
  routing, and clarification.
- One demonstrated multi-turn session including an intent override.
- Setup instructions, one evaluator command, architecture summary, limitations,
  model and cost disclosure, and team contributions.

## Explicit Non-Goals

- Large frontend or dashboard.
- External production vector database.
- Full-parameter LLM fine-tuning.
- Multi-agent orchestration, reinforcement learning, or a knowledge graph.
- Catalog mutation or target-specific rules derived from private data.
