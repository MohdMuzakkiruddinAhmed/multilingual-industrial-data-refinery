# Datasets

- `benchmark-v2-final/`: canonical v2 dataset, 1,728 cases and 1,920 raw files.
  `sources.json` is the input manifest; `expected.json` is the separate oracle;
  `dataset_card.json` records hashes, seed, composition, and limitations.
- `sources.json` / `expected.json`: original 14-case PoC fixtures.
- `benchmark-v2/`: preserved preflight generator output, not the dataset used
  for the reported final v2 experiments.

All supplied records are synthetic. Product-family splits and ground-truth
definitions are described in `../EXPERIMENTS.md`.
