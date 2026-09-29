# End-to-end experiment protocol

## What runs end to end

Semantic synthetic product specification → raw text/JSON/Markdown source files →
hash-verified ingestion → NIM or rules extraction → evidence validation → canonical
record → identity/variant matching → localized market view → simulated publication
or review → independent oracle scoring → comparison report and plots.

The workflow reads the actual documents from disk. Sources, expected answers,
reference catalog, and experiment manifests have separate roles. Expected answers
are never sent to NIM. The supplied API key remains an environment variable.

## Dataset v2

`data/benchmark-v2-final/` contains 1,728 cases, 1,920 raw documents, 24 motor
families, four languages (English/German/Spanish/Arabic), and 18 scenarios.

Source styles include labeled text, shuffled synonyms with equals signs, Markdown
table rows, flat JSON, and natural narrative paragraphs. Numeric variations include
kW/W, kV/V, decimal commas, nonbreaking spaces, and Arabic-Indic digits.

Cases cover missing attributes, ambiguous quantities, conflicting active sources,
superseded revisions, withdrawn and unauthorized sources, product variants,
identifier collisions, different manufacturers/products, fictional market
certificate requirements, and embedded prompt injection.

The seeded semantic specification comes first. The source documents are rendered
from it, and the oracle is derived from the specification and scenario rules,
never from the production parser or an LLM's own answers. Source-level ground
truth retains explicitly stated contradictory values; canonical ground truth
removes unresolved conflicts. This distinction matters for extraction metrics.

Product families are partitioned as 864 train / 432 development / 432 test cases.
Translated siblings and variants stay in the same split. No model is trained in
this project; the train split is reserved for future work. Rendering templates are
shared across splits, so this tests unseen products, not unseen writing styles.

The primary live run uses one case from every language × scenario cell: **72
cases**, balanced across six test families. All 432 test cases are evaluated with
the deterministic baseline. The smaller live sample limits API cost while keeping
all scenarios and languages represented. It does not support precise real-world
accuracy estimates.

The earlier `data/benchmark-v2/` directory is a preflight generator artifact that
lacks the final source-level oracle. Use `data/benchmark-v2-final/` for all reported
v2 experiments; manifests identify the exact input and oracle hashes.

## Workflows

| Workflow | Extraction | Repair | Advisory evidence review | Acceptance rules |
| --- | --- | --- | --- | --- |
| Rules | Deterministic approved grammar | None | None | Same v2 gate |
| NIM single pass | One NIM extraction | None | None | Same v2 gate |
| NIM conditional | Exactly the same first NIM response | At most one request if omissions/rejections are repairable | Requested for blocked records | Same v2 gate |

The paired design shares the first NIM response, including transport failures,
between both model workflows. This isolates the contribution of extra steps and
reduces cost. It is not a comparison of independent API draws. Model, prompt,
reference access, deterministic checks, timeout, and transport retry policy remain
the same. There is no post-hoc substitution of successful retries in the metrics.

This initial comparison does not include an always-on two-pass workflow with a
matched inference budget. Therefore, improvements cannot be attributed uniquely
to agency rather than additional inference/feedback. The experiment measures this
specific conditional protocol's quality/cost tradeoff, not a general agent claim.

Each experiment writes its selected IDs, hashes, model, prompt version, request
budget, and metric protocol **before** requests or scoring. Output directories
cannot be overwritten. A checkpoint and request audit are written after each
completed case. Automatic resume is not implemented; interrupted experiments
remain partial and should not be reported as full runs.

## Metrics and interpretation

The primary endpoint is exact case correctness: state, identity outcome, and all
canonical attributes must match the oracle. Secondary metrics are:

- Source-level extraction precision, recall, F1: exact source/field/value/unit
  tuples from the current proposal set, deduplicated after repair. Superseded
  rejected proposals remain in the audit but are excluded from this score.
- Accepted canonical attribute precision, recall, F1. Wrong predictions count as
  false positives and missing correct facts as false negatives.
- Publication precision/recall, unsafe approvals, unnecessary review, and
  auto-acceptance coverage. Report precision alongside coverage.
- Identity accuracy, macro F1, confusion counts, and false same-product decisions.
- Structural evidence-link coverage and localization value-preservation rate.
- Logical requests/tokens for each standalone workflow; physical requests/tokens
  actually issued; per-case p50/p95 latency and total wall time.
- Breakdowns by source language, destination market, scenario, format, and family.

The difference in exact-case accuracy between the paired NIM arms receives a
seeded group-bootstrap interval, resampling product families rather than treating
translated siblings as independent. With only six synthetic groups, that interval
is descriptive and does not establish significance or production superiority.

Logical arm costs count the shared initial request in each arm. Physical totals
count it once. Reported tokens may omit usage on timed-out requests. No dollar
price is assumed and no unverified pricing claim is made.

Single-pass logical latency measures initial inference; conditional latency adds
repair/review and local orchestration. Rules latency measures local processing.
Source-file reads and report/checkpoint writes are included in physical wall time,
not logical inference latency. The small single-pass deterministic processing cost
is not included in its latency estimate.

## Evidence-gate ablation

A separate deterministic experiment corrupts proposals with wrong values, forged
quotes, wrong source IDs, and wrong units. The proper validator is compared with
a simulated no-check copier. This is a controlled fault-injection test, not an
estimate of NIM's hallucination rate. The unchecked comparator cannot publish.

## Reproduce

```powershell
# Existing dataset is frozen; use a fresh folder for a new seed.
python -m refinery.experiments generate --out data/my-benchmark --seed 20260928 --groups 24

# Full deterministic test split.
python -m refinery.experiments run --data data/benchmark-v2-final --split test --per-stratum 0 --out outputs/experiments/my-rules-run

# Set NVIDIA_API_KEY securely as shown in README.md, then run the paired comparison.
python -m refinery.experiments run --data data/benchmark-v2-final --split test --live --max-calls 180 --timeout 20 --out outputs/experiments/my-live-run

python -m unittest discover -s tests -v
```

Use a new output directory for each repetition. `--per-stratum 2` selects 144
cases; `--per-stratum 0` selects all 432 test cases and requires a larger explicit
request budget for NIM. `--limit` is only for engineering smoke tests and breaks
balanced sampling. The standard library runs inference and scoring; optional
Matplotlib generates PNG/SVG figures (available in this environment).

## Boundaries

The current verifier supports explicit structured facts and a finite terminology
library. Narrative descriptions deliberately stay in the dataset and the recall
denominator; it is correct to expose that limitation. Rules can outperform an LLM
on formats the rules were written to parse. A favorable synthetic score does not
establish the value of agents, real-document extraction quality, Arabic language
proficiency, translation quality, regulatory compliance, or production readiness.
Qualified bilingual reviewers and authorized real catalogs are the next external
validation step. The current workflow is bounded orchestration, not four fully
autonomous agents. Publication is a local simulation.
