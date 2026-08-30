# Competition Data

## `public_set.jsonl`

Contains 200 labeled development sessions: 80 Buying, 80 Browsing, 30 Intent Override, and 10 Boundary sessions.

Each session contains a safe aggregate `user_profile` and public labels for local development. Direct user identifiers, timestamps, free-text reviews, raw purchase history, hidden intent cards, and simulator-policy internals are not shipped in this participant file.

## `catalog.jsonl`

Download `catalog.jsonl.gz` from the GitHub Release and decompress it as `catalog.jsonl` in this directory. Expected row count: 50,000.

Never place API keys, private evaluation data, or participant outputs in this directory.

## Generated coverage-stress catalog

`data/generated/catalog-coverage-stress.jsonl` is a local diagnostic artifact.
Build it with `python -m scripts.build_coverage_stress_catalog`. It preserves all
catalog identifiers and masks only over-covered fields on the 200 public targets;
it is not an official catalog or submission artifact.
