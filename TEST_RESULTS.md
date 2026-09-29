# PoC verification — September 27, 2026

## Automated checks

`python -m unittest discover -s tests -v`: **31 tests passed**.

Tests exercise evidence fabrication, changed values, partial quotes, wrong units,
malformed proposals, omitted contradictory sources, ambiguous source expressions,
source withdrawal and supersession, identifier collisions, localized/canonical
tampering, missing market requirements, bounded repair and transport retries,
authentication errors, provider failure, request budgets, and HTML escaping.

## Measured runs

| Run | Fully correct cases | Approved | Review required | API requests | Reported tokens |
| --- | --- | --- | --- | --- | --- |
| Offline rule baseline | 14 / 14 | 8 | 6 | 0 | 0 |
| Final full NIM Super run | 13 / 14 | 8 | 6 | 19 | 11,533 |
| Separate retry of service-failed case | 1 / 1 | 0 | 1 | 2 | 1,088 |

The final full NIM run took **38.734 seconds** and used
`nvidia/nemotron-3-super-120b-a12b`. It encountered three HTTP 503 responses:
one recovered after the bounded retry; two consecutive failures prevented
extraction for `market_missing_certificate`. That record correctly stayed in
review, but its missing extracted facts and unresolved identity failed the exact
oracle comparison. The full run therefore exited with status 1. Its publication
state matched the expected state on all 14 cases.

The separate targeted retry extracted all six supported attributes and correctly
blocked publication because the fictional es-MX profile requires a certificate.
It passed and exited with status 0. **This does not retroactively change the
full-run score to 14/14.**

In the final full run:
- Auto-acceptance coverage: **57.1%** (8 / 14).
- Correctness among approved records: **100% on these fixtures**.
- Correctness among accepted attributes: **100%**.
- Attribute recall: **92%**, reduced by the failed API request.
- Evidence-link coverage: **100%**.
- Unsupported accepted attributes: **0**.
- False same-product decisions: **0**. No destructive merge operation is implemented.

## Artifacts

- [Final full NIM dashboard](outputs/nim-final/report.html)
- [Final full NIM results](outputs/nim-final/run.json)
- [Final NIM request log](outputs/nim-final/calls.json)
- [Separate targeted retry](outputs/nim-targeted-retry/report.html)
- [Offline dashboard](outputs/offline/report.html)

Earlier diagnostics remain separate:
- `outputs/nim/`: initial Lightning run, stopped after eight completed cases
  following malformed output and repeated timeouts; checkpoints and request logs
  are retained. This is an incomplete run, not a full benchmark result.
- `outputs/nim-json-check/`: two-case Lightning JSON-mode check, 1/2 passing.
- `outputs/nim-super/`: first Super run before transport retry was added,
  13/14 passing; a single HTTP 503 blocked the Arabic case.

## Dashboard and credential checks

The generated dashboard was served successfully over loopback (HTTP 200), its
embedded report was parsed and checked, and its JavaScript passed `node --check`.
No browser was available through the computer-use tools, so visual browser
inspection and interactive UI verification were **not** completed.

A recursive workspace scan found no API key strings. The supplied key was used
only in process environment variables for NVIDIA requests, not saved in project
files. Request logs exclude authorization headers and server reasoning fields.

## Interpretation

These are handcrafted synthetic regression fixtures, not representative real-world
data or a statistical model benchmark. They establish that the implemented narrow
grammar, provenance rules, and publication controls behave as specified on the
tested cases. They do not establish arbitrary-document extraction quality,
general Arabic proficiency, production security, or superiority of one model.
The model choice is a provisional implementation decision based on these diagnostic
runs. See README.md for the deliberately limited parser and deployment scope.
