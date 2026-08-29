# Coverage-Stress Catalog and Dual Evaluation Design

Date: 2026-08-29

Status: Approved for implementation planning

## Problem

The 200 public sessions do not target a field-presence distribution that matches
the frozen 50,000-product catalog. All 200 targets have features and 178 have a
price, whereas catalog-wide coverage is 89.562% for features and 21.054% for
price. Results on the public set may therefore overstate robustness to missing
catalog metadata.

Adding distractors or copying the catalog cannot change the target distribution:
the evaluator still scores the same `ground_truth.parent_asin` values. A useful
second environment must alter the visible metadata of those target records in a
controlled way while preserving target identity and the original official run.

## Decision

Add a deterministic coverage-stress catalog and make evaluator-facing experiment
commands run both the official and stress catalogs by default.

The stress catalog will only remove existing values from over-covered public
targets. It will never invent, impute, copy, or synthesize a missing value. The
official catalog, public dataset, evaluator, product identifiers, and non-target
catalog records remain unchanged.

The stress result is a sensitivity diagnostic, not an estimate of the private
score. Official and stress metrics remain separate and are never combined into a
single score.

## Goals

- Match catalog-wide marginal field-presence rates on the 200 public targets as
  closely as possible using deterministic masking only.
- Preserve all 50,000 products, their order, and every `parent_asin`.
- Keep all non-target product records equivalent at the parsed JSON-value level.
- Rebuild or reject a stale stress catalog when the source catalog, public set,
  algorithm version, or seed changes.
- Run the current default evaluation, clarification ablation, and popularity
  sweep against official and stress catalogs by default.
- Preserve an explicit official-only mode for historical reproduction.
- Record enough aggregate evidence to audit the generated distribution without
  storing a second 60 MB catalog in Git.

## Non-goals

- Predict or recreate the organizer's 800 private sessions.
- Claim that marginal coverage matching reproduces joint field distributions,
  value distributions, target popularity, or private sampling policy.
- Generate descriptions or other metadata for fields that are missing on public
  targets.
- Replace public target products or rewrite their labels, profiles, scenario
  types, or identifiers.
- Modify `evaluator/` or use evaluator-only fields inside `starter/`.
- Use the stress catalog as a submission artifact or report its result as the
  official TechnicalScore.

## Coverage Target and Masking Rule

Coverage uses the existing `analysis.catalog_profile._present` semantics:
`None`, blank strings, empty lists, and empty dictionaries are missing; other
values are present.

For each field:

1. Compute catalog-wide coverage from the source 50,000 products.
2. Set the desired public-target present count to
   `round(catalog_present / catalog_rows * target_count)`.
3. If the public-target present count exceeds the desired count, mask exactly
   the difference.
4. If it is below the desired count, leave it unchanged and record the
   unfillable shortfall. No value is fabricated.

With the current data, the expected plan is:

| Field | Original targets | Desired | Masked | Stress targets | Shortfall |
| --- | ---: | ---: | ---: | ---: | ---: |
| categories | 200 | 200 | 0 | 200 | 0 |
| title | 200 | 200 | 0 | 200 | 0 |
| details | 200 | 193 | 7 | 193 | 0 |
| store | 200 | 199 | 1 | 199 | 0 |
| features | 200 | 179 | 21 | 179 | 0 |
| description | 89 | 104 | 0 | 89 | 15 |
| price | 178 | 42 | 136 | 42 | 0 |
| average_rating | 200 | 200 | 0 | 200 | 0 |
| rating_number | 200 | 200 | 0 | 200 | 0 |

The generator selects masked products independently for each field by sorting
present target ASINs on the digest of the UTF-8 string
`algorithm_version + "\0" + seed + "\0" + field + "\0" + parent_asin`.
This provides exact marginal counts without depending on input traversal order
or Python's randomized hash implementation. Field-specific ranking avoids
forcing all missing fields onto the same products.

Type-appropriate empty values are used:

- list fields become `[]`;
- dictionary fields become `{}`;
- scalar fields become `null`.

The current public dataset contains 200 distinct targets. The generator will
fail clearly if targets are missing from the catalog or duplicate target IDs
appear, because product-level masking would not then equal session-weighted
coverage without a separate weighting design.

## Components

### `analysis/coverage_stress.py`

Pure, testable coverage and generation logic:

- calculate source and public-target profiles;
- calculate desired counts and deterministic mask sets;
- apply type-appropriate masking;
- validate invariants;
- write the stress catalog and aggregate manifest;
- verify whether an existing generated artifact matches its inputs.

The module must not import `starter.Agent` or run the evaluator.

### `scripts/build_coverage_stress_catalog.py`

CLI around the pure generator. Defaults:

- source catalog: `data/catalog.jsonl`;
- dataset: `data/public_set.jsonl`;
- output catalog: `data/generated/catalog-coverage-stress.jsonl`;
- manifest: `reports/experiments/coverage-stress-catalog.json`;
- fixed seed: `techjam-coverage-stress-v1`.

The command prints a compact before/after table and exits non-zero on an
invariant failure.

### `analysis/catalog_variants.py`

Shared orchestration for evaluator-facing scripts. It resolves:

- `official`: the unmodified `--catalog` path;
- `coverage_stress`: a verified generated artifact, rebuilding it when source
  hashes, dataset hash, algorithm version, or seed do not match the manifest.

Supported modes are `dual`, `official`, and `stress`. `dual` is the default.
This module owns argument-independent catalog preparation; experiment-specific
metric calculation stays in each experiment script.

### `scripts/run_dual_catalog_evaluation.py`

Runs the current default `Agent` on both catalog variants without modifying the
official evaluator. It imports and calls the existing evaluator functions with
the same public samples and scoring rules.

The output contains aggregate overall and scenario metrics for each catalog,
plus stress-minus-official deltas. Session-level results are not written to the
tracked report.

### Existing experiment scripts

Update these entry points to use `analysis.catalog_variants`:

- `scripts/run_clarification_ablation.py`;
- `scripts/run_popularity_sweep.py`.

In dual mode, each script runs its existing experiment independently for both
catalog variants. It reports deltas at the same leaves it already reports:
policy and split for clarification; weight, split, and difficulty for popularity.
The underlying single-catalog functions remain usable and testable.

`--catalog-mode official` preserves the legacy single-catalog output shape and
is the documented way to reproduce historical JSON. Dual mode uses a new
top-level schema with `catalogs.official`, `catalogs.coverage_stress`, and
`deltas`.

Future evaluator-facing scripts must use the same catalog-variant resolver.
Unit tests and catalog-independent diagnostics do not run twice.

## Data Flow

1. A dual experiment requests catalog variants.
2. The resolver hashes the source catalog and public dataset and reads the
   manifest if present.
3. If the manifest and output are current, it reuses the stress catalog.
4. Otherwise, the generator loads source products and public target IDs,
   calculates masks, writes the derived catalog, validates it, and writes the
   manifest.
5. The experiment loads and evaluates the official catalog.
6. It separately constructs a fresh `Agent` and evaluator catalog index for the
   stress catalog. No database or Agent state is shared between variants.
7. It writes separate aggregate results and paired metric deltas.

The evaluator currently materializes hidden intent cards and customer replies
from the catalog passed to it. Using the stress catalog for both the Agent and
evaluator therefore keeps simulated disclosures consistent with the masked
product record. This also means the stress run tests a different information
environment, not merely a different retrieval index; reports must state this.

## Manifest and Output Evidence

The catalog manifest includes:

- schema and algorithm versions;
- seed;
- relative input and output paths;
- SHA-256 hashes for source catalog, dataset, and generated catalog;
- catalog row count, session count, distinct target count, and matched count;
- per-field catalog coverage, desired target count, original target count,
  masked count, stress target count, and unfillable shortfall;
- invariant-check results.

It stores aggregate counts only, not the list of target or masked ASINs. The
algorithm and seed are sufficient to reproduce that selection from the public
inputs.

`data/generated/` is added to `.gitignore`; the manifest, aggregate dual-run
JSON, report, code, and tests are tracked.

## Interpretation and Experiment Decisions

Official validation TechnicalScore remains the primary selection metric. Stress
results are reported as a robustness dimension. This design does not define an
automatic combined score or a universal stress non-regression threshold.

Every evaluator-facing report must state:

- official metrics;
- coverage-stress metrics;
- stress-minus-official deltas overall and by scenario or existing experiment
  split;
- whether a change improves only one environment;
- that the stress environment is public-target-aware and cannot estimate the
  private score.

A method that improves official results but regresses under stress requires an
explicit judgment and explanation; the runner does not automatically keep or
reject it.

## Failure Handling

Generation stops without replacing a valid prior output when:

- a public target is absent from the source catalog;
- target IDs are duplicated;
- source row identifiers are duplicated;
- row counts or identifier sets change after generation;
- a non-target record changes;
- a masked field becomes present;
- any field is filled or its present count increases;
- final counts do not match the computed plan.

The generator writes to a temporary sibling file and replaces the derived
catalog only after validation, so interruption cannot leave a partial file at
the expected output path.

## Testing

### Unit tests

Use small JSONL fixtures to verify:

- exact desired-count calculation and rounding;
- deterministic byte-identical output for the same seed;
- stable counts but potentially different selected targets for another seed;
- masking only present fields on target products;
- no modification to non-target parsed records or product order;
- no filling of an under-covered field and correct shortfall reporting;
- correct empty representation for list, dictionary, and scalar fields;
- failure on missing targets, duplicate targets, and duplicate catalog IDs;
- manifest staleness detection;
- `official`, `stress`, and `dual` variant resolution.

### Integration verification

1. Run the complete unit test suite.
2. Build the real stress catalog twice and confirm identical output hashes.
3. Confirm 50,000 rows and the same ordered ASIN sequence in both catalogs.
4. Confirm the current expected target counts in the manifest.
5. Run the current best Agent on both variants for all 200 public sessions.
6. Run targeted clarification and popularity commands in dual mode.
7. Run `git diff --check` and confirm the generated catalog is ignored.

## Documentation Changes

- Add construction and interpretation guidance to `data/README.md`.
- Add dual and official-only commands to `docs/EXPERIMENT_WORKFLOW.md`.
- Add the coverage-stress baseline, limitations, and evidence links to
  `docs/experiment_history.md`.
- Add an experiment report and raw aggregate JSON under `reports/experiments/`.

The report must not overwrite or relabel historical official results.

## Known Limitations

- Only marginal presence counts are matched; correlations between fields are
  not modeled.
- Description remains under-covered because filling 15 missing descriptions is
  forbidden.
- Mask selection is deterministic but artificial and may create combinations
  absent from the source distribution.
- The public target set is already popularity-biased, and masking metadata does
  not correct that bias.
- Repeatedly tuning against the stress catalog can still overfit these 200
  public targets.
- The stress environment may be harsher or simply different from the private
  evaluation. It is a robustness probe, not a forecast.
