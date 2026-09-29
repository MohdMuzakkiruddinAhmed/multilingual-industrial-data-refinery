# End-to-end experiment results — September 27, 2026

The implementation was frozen before the held-out test runs. Its Python source
hash was checked afterward and still matched the pre-run manifest. No pipeline or
prompt changes were made in response to held-out results.

## What was built and tested

1,728 seeded synthetic motor-catalog cases; 1,920 actual source documents; 24
product families; four source languages; five target market profiles; 18 scenarios.
The dataset has separate semantic ground truth, source-level extraction truth,
canonical expected outcomes, and disjoint train/development/test product families.

The complete 432-case test split was run through the deterministic workflow. A
balanced 72-case subset (18 per language; 12 per test family) was used for the live
NVIDIA NIM experiment. Both NIM workflows share exactly the same first response.
All inference used `nvidia/nemotron-3-super-120b-a12b`.

## Paired comparison on the same 72 held-out cases

| Metric | Rules | NIM single pass | NIM conditional |
| --- | ---: | ---: | ---: |
| Exactly correct cases | 68/72 | 67/72 | 68/72 |
| Exact-case accuracy | 94.44% | 93.06% | 94.44% |
| Raw extraction F1 | 96.91% | 99.25% | 98.48% |
| Accepted-attribute precision | 100% | 100% | 100% |
| Accepted-attribute recall | 93.55% | 93.28% | 93.55% |
| Accepted-attribute F1 | 96.67% | 96.52% | 96.67% |
| Publication precision | 100% | 100% | 100% |
| Publication recall | 90.0% | 87.5% | 90.0% |
| Automatic acceptance | 50.0% | 48.61% | 50.0% |
| Matching accuracy | 94.44% | 93.06% | 94.44% |
| Unsupported accepted facts | 0 | 0 | 0 |
| False same-product decisions | 0 | 0 | 0 |
| Unsafe publication decisions | 0 | 0 | 0 |
| Evidence-link coverage | 100% | 100% | 100% |
| Localization value preservation | 100% | 100% | 100% |
| Logical API calls | 0 | 66 | 103 |
| Logical reported tokens | 0 | 76,013 | 104,542 |
| Per-case latency p50 | 0.00052 s | 2.75 s | 3.16 s |
| Per-case latency p95 | 0.00125 s | 7.15 s | 11.58 s |

Actual physical usage across the paired experiment was **103 requests, 104,542
reported tokens, and 317.723 seconds**. Two HTTP 503 responses recovered through
the predefined transport retry. No records were dropped or replaced by later runs.
The single-pass arm's first-response costs are already included in conditional
costs, so summing both logical columns would double-count shared requests.

Eight cases had withdrawn or unauthorized sources and correctly made no initial
inference request. Sixty-four eligible-source extractions plus two transient
retries account for the single-pass arm's 66 calls. The conditional arm added
nine extraction repairs and 28 advisory reviews.

## What the results show

**The gate protected accepted outputs in this synthetic test.** Every accepted
attribute matched the oracle and retained a valid evidence link. The deliberately
unsafe source scenarios were held for review rather than published.

**Conditional repair had a small measured benefit and a material cost.** It
recovered one German JSON case that the single pass did not fully accept, adding
one correct fact and one approved record. That gain cost 37 extra calls and 28,529
extra reported tokens. The paired accuracy difference was +1.39 percentage points;
the descriptive product-family bootstrap interval was [0.00, 4.17] points. Six
synthetic groups do not support a claim of general statistical superiority.

**Narrative verification is the main coverage limit.** All four narrative cases
failed the final exact-case check for every workflow. The single-pass NIM model
extracted substantially more source facts than rules, but the approved grammar
could not validate full narrative paragraphs. Adding model reasoning alone did
not resolve that acceptance boundary. Conditional repair also dropped some
unverifiable narrative proposals, explaining its lower active-proposal raw F1
despite slightly better final canonical recall.

**Rules are a strong baseline for structured sources.** Rules and conditional NIM
produced the same final exact-case score on this benchmark, while rules used no
API calls. These results do not justify claiming that agents outperform a rules
pipeline. They support testing NIM for inputs where deterministic extraction is
insufficient, provided evidence validation can also handle those inputs.

## Full deterministic test and fault injection

On all **432 held-out cases**, rules produced **408 exact matches (94.44%)**,
**96.67% accepted-attribute F1**, and **zero unsafe approvals**. All 24 missed cases
were narrative descriptions. There were 216 approved records and 216 review cases;
24 of those review cases were ideally publishable according to semantic truth.

The paired-subset fault experiment deliberately corrupted **208 proposals**.
The evidence gate rejected all 208; the simulated no-check copier accepted all
208. The complete rules test included 1,248 such corrupted proposals, also with
zero guarded acceptances. This is a deterministic control experiment, **not** an
estimated NIM hallucination rate. The unchecked arm never exports publications.

**49 automated tests pass**, including source hash/path validation, disjoint
splits, independent oracle semantics, malformed evidence, unit conversion,
tampering, repair behavior, transport retries, and evaluation denominators.

## Artifacts

- [Interactive paired experiment dashboard](outputs/experiments/test-paired-nim/report.html)
- [Detailed generated results and breakdowns](outputs/experiments/test-paired-nim/RESULTS.md)
- [Machine-readable metrics](outputs/experiments/test-paired-nim/summary.json)
- [Frozen experiment manifest](outputs/experiments/test-paired-nim/manifest.json)
- [NIM request audit](outputs/experiments/test-paired-nim/calls.json)
- [PNG comparison figure](outputs/experiments/test-paired-nim/comparison.png)
- [SVG comparison figure](outputs/experiments/test-paired-nim/comparison.svg)
- [All 432 rules cases](outputs/experiments/test-rules-full/report.html)
- [Dataset card](data/benchmark-v2-final/dataset_card.json)
- [Reproduction instructions and metric definitions](EXPERIMENTS.md)

## Limits and next experiments

The scenario frequencies were deliberately balanced; 50% automatic acceptance is
not a forecast of production review burden. Product families are disjoint, but
rendering templates are shared across splits. Only motors were studied. Semantic
truth is generator-defined and has not been independently checked by bilingual
technical reviewers. Market certificates are fictional. Localization metrics
measure value preservation, not natural-language translation quality.

The comparison lacks an always-on two-pass matched-budget baseline, so the repair
gain cannot be attributed specifically to agentic routing rather than additional
inference and feedback. Logical single-pass latency excludes its small local
validation cost; physical wall time includes all checkpoint/report overhead.
Hosted model aliases may change, and missing token usage on failed requests is
not recoverable from the API logs.

The next useful experiments are a matched-budget fixed workflow, evidence
verification for clear prose, a larger held-out live sample spanning every
family/scenario combination, repeated inference runs, and authorized real catalog
data with independent bilingual annotation. The current results are suitable for
PoC validation and designing those experiments, not for a production accuracy claim.
