# Saved runs

Start with `experiments/test-paired-nim/report.html` or its `RESULTS.md`.
The final 72-case paired comparison, full 432-case rules evaluation, development
runs, and original PoC diagnostics are all retained. `calls.json` stores model
requests/responses without authorization headers. Checkpoints are included,
including the incomplete early `nim/` run, which is not a full benchmark.

See `../EXPERIMENT_RESULTS.md` for the final interpretation and
`../TEST_RESULTS.md` for the historical PoC diagnostics. Historical run manifests
describe the code/settings that produced them; not every early run used the final
implementation. New output folders are ignored by Git by default.
