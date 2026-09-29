# Proof-of-concept plan

## Objective
Implement the draft's core preservation contract using synthetic motor catalogs,
NVIDIA hosted NIM, executable acceptance rules, and inspectable evidence.

## First implementation
1. Versioned synthetic source records and separate expected answers.
2. Bounded NIM extraction: structured proposals with verbatim evidence quotes.
3. Deterministic evidence validation, decimal unit conversion, conflict detection,
   source supersession, and protected-attribute matching.
4. Canonical records and terminology-controlled views: en-US, de-DE, es-ES,
   es-MX, and ar-SA. Spanish profiles intentionally have different requirements.
5. Conditional evidence review for problematic records. No model may approve
   a record or call enterprise systems. Local publication is a simulated export.
6. Offline regression tests, a live NIM synthetic evaluation, and an HTML report.

## Acceptance criteria
- Every accepted attribute links to an immutable source hash, exact text span,
  and normalization rule; unsupported proposals stay outside accepted facts.
- Missing/ambiguous required fields and conflicting active sources block export.
- Different voltage/frequency variants never merge; matching requires identifiers.
- Localization keeps the canonical values and identifiers intact.
- Withdrawing evidence changes dependent records to review-required on reprocessing.
- API errors are visible; no implicit model/provider/offline fallback.
- Expected synthetic answers never enter model prompts.
- Report accuracy together with auto-acceptance coverage, language breakdown,
  request usage, and limitations. Synthetic success is not production evidence.

## Later work
Native PDF/spreadsheet ingestion; signed source registry; licensed taxonomy;
additional product families; qualified bilingual review; durable approval service;
real catalog evaluation; fixed-workflow versus conditional-agent ablation;
local GPU NIM deployment; capability router and embedding retrieval.

## Implementation status
The initial slice is implemented: CLI, source fixtures, NIM integration, bounded
repair/review, deterministic acceptance, market views, simulated publication,
evaluation, and interactive HTML artifacts. See `TEST_RESULTS.md` for measured
results and diagnostic failures. The full draft's four-agent architecture and
empirical research evaluation remain later work.

The second implementation phase adds a semantic-first synthetic generator,
source-file ingestion, expanded structured formats, group-disjoint splits,
independent source/canonical oracles, a paired NIM experiment runner, count-based
metrics, family-bootstrap comparisons, fault injection, and PNG/SVG reports.
See EXPERIMENTS.md and the generated test reports for the current experiment.
