"""Reproducible paired end-to-end experiments using actual source files."""
import argparse
import copy
import json
import platform
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .benchmark_data import write_benchmark, load_case_documents, select_cases, fingerprint
from .engine import refine_case, register_sources, rule_proposals, validate_proposals
from .experiment_metrics import score, paired_comparison
from .nim import NimClient, NimError, EXTRACT_SYSTEM, REVIEW_SYSTEM, PROMPT_VERSION
from .report import write_report


def dump(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def usage(calls, seconds):
    return {"logical_requests": len(calls), "logical_tokens": sum((c.get("usage") or {}).get("total_tokens", 0) for c in calls),
            "logical_seconds": round(seconds, 6), "transport_errors": sum("error" in c for c in calls)}


class SharedFirstResponse:
    """Exact same first proposal/error in both arms; additional calls stay live."""
    def __init__(self, proposals, failure, client=None):
        self.proposals, self.failure, self.client = proposals, failure, client
        self.first = True

    def extract(self, sources, feedback=None):
        if self.first:
            self.first = False
            if self.failure:
                raise NimError(self.failure)
            return copy.deepcopy(self.proposals)
        if not self.client:
            raise RuntimeError("Single-pass arm unexpectedly tried to repair")
        return self.client.extract(sources, feedback)

    def review(self, issues, sources):
        return self.client.review(issues, sources)


def fault_experiment(cases, oracle):
    """Controlled acceptance-gate stress test; deliberately unchecked arm NEVER exports."""
    counts = Counter()
    examples = []
    for case in cases:
        registry = register_sources(case["sources"])
        proposals = rule_proposals([s for s in registry if s["eligible"]])
        numeric = next((p for p in proposals if p["field"] == "power"), None)
        if not numeric:
            continue
        for fault in ("wrong_value", "forged_quote", "wrong_source", "wrong_unit"):
            corrupt = copy.deepcopy(numeric)
            corrupt["value"] = "999999"
            if fault == "forged_quote":
                corrupt["quote"] = "power: 999999 W"
            elif fault == "wrong_source":
                corrupt["source_id"] = "unregistered-source"
            elif fault == "wrong_unit":
                corrupt["unit"] = "kW"
            accepted, rejected, _ = validate_proposals([corrupt], registry)
            counts["injected_claims"] += 1
            counts["guarded_wrong_acceptances"] += "power" in accepted
            counts["unchecked_wrong_acceptances"] += 1  # Explicit simulated no-check comparator.
            counts["rejected"] += bool(rejected)
            if len(examples) < 8:
                examples.append({"case_id": case["id"], "fault": fault, "reason": rejected[0]["reason"] if rejected else None})
    return {"type": "deterministic injected-fault ablation, NOT observed NIM hallucination rate",
            "counts": dict(counts), "examples": examples,
            "unchecked_arm": "Simulation of copying proposals directly; no publication artifacts are created."}


def code_hash():
    return fingerprint({p.name: p.read_text(encoding="utf-8") for p in sorted(Path(__file__).parent.glob("*.py"))})


def run_experiment(args):
    root, out = Path(args.data), Path(args.out)
    inputs = json.loads((root / "sources.json").read_text(encoding="utf-8"))
    oracle = json.loads((root / "expected.json").read_text(encoding="utf-8"))
    card = json.loads((root / "dataset_card.json").read_text(encoding="utf-8"))
    if fingerprint(inputs) != card["input_sha256"] or fingerprint(oracle) != card["oracle_sha256"]:
        raise ValueError("Dataset or oracle changed since freezing")
    cases = select_cases(inputs, args.split, args.per_stratum)
    if args.limit:
        cases = cases[:args.limit]
    if not cases:
        raise ValueError("No experiment cases selected")
    if any(not src.get("synthetic") for c in cases for src in c["sources"]):
        raise ValueError("Experiment runner accepts synthetic documents only")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Use a fresh experiment directory; prior experiments are immutable")
    client = NimClient(model=args.model, timeout=args.timeout, max_calls=args.max_calls) if args.live else None
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "dataset_sha256": fingerprint(inputs),
                "oracle_sha256": fingerprint(oracle), "code_sha256": code_hash(), "python": platform.python_version(),
                "prompt_version": PROMPT_VERSION, "prompt_sha256": fingerprint([EXTRACT_SYSTEM, REVIEW_SYSTEM]),
                "split": args.split, "per_stratum": args.per_stratum, "case_ids": [c["id"] for c in cases],
                "groups": sorted({c["group"] for c in cases}), "model": client.model if client else None,
                "max_calls": args.max_calls, "timeout": args.timeout, "live": args.live,
                "comparison": "Same first NIM response shared between single-pass and conditional arms; no oracle supplied to models.",
                "workflow_versions": {"rules": "v2", "nim_single_pass": "one extraction + deterministic checks", "nim_conditional": "shared extraction + at most one repair + advisory review if blocked"},
                "limits": card["limitations"]}
    # Manifest is written BEFORE any model request or test-set evaluation.
    dump(out / "manifest.json", manifest)
    dump(out / "protocol.json", {"primary": "exact_case_accuracy", "secondary": ["attribute_f1", "raw_extraction_f1", "publication_precision", "publication_recall", "auto_acceptance_rate", "matching_accuracy", "logical_requests", "logical_tokens", "latency_seconds_p50", "latency_seconds_p95"],
                                 "failures": "Included in all denominators; no post-hoc substitution of successful retries.",
                                 "scope": "Motor catalogs; language and market are independent axes; certificates are fictional."})
    arms = {"rules": []}
    if client:
        arms.update(nim_single_pass=[], nim_conditional=[])
    started = time.perf_counter()
    for index, original in enumerate(cases, 1):
        case = load_case_documents(original, root)
        before = time.perf_counter()
        rules = refine_case(case, inputs["catalog"])
        rules["experiment_usage"] = usage([], time.perf_counter() - before)
        arms["rules"].append(rules)
        if client:
            registry = register_sources(case["sources"])
            eligible = [s for s in registry if s["eligible"]]
            first_call = len(client.calls)
            before = time.perf_counter()
            proposals, failure = [], None
            if eligible:
                try:
                    proposals = client.extract(eligible)
                except NimError as exc:
                    failure = str(exc)
            initial_seconds = time.perf_counter() - before
            first_calls = copy.deepcopy(client.calls[first_call:])
            single = refine_case(case, inputs["catalog"], SharedFirstResponse(proposals, failure), review=False, repair=False)
            single["experiment_usage"] = usage(first_calls, initial_seconds)
            arms["nim_single_pass"].append(single)
            extra_start = len(client.calls)
            before = time.perf_counter()
            conditional = refine_case(case, inputs["catalog"], SharedFirstResponse(proposals, failure, client))
            conditional["experiment_usage"] = usage(first_calls + client.calls[extra_start:], initial_seconds + time.perf_counter() - before)
            arms["nim_conditional"].append(conditional)
            for call in client.calls[first_call:]:
                call["case_id"] = case["id"]
            dump(out / "calls.json", client.calls)
        for records in arms.values():
            records[-1]["benchmark"] = {k: case[k] for k in ("scenario", "language", "format", "group", "split")}
        dump(out / "checkpoint.json", arms)
        if index == 1 or index % (4 if client else max(4, len(cases) // 12)) == 0 or index == len(cases):
            detail = " / ".join(f"{name}:{records[-1]['state']}" for name, records in arms.items())
            print(f"[{index}/{len(cases)}] {case['language']} {case['scenario']} | {detail}", flush=True)
    summaries = {}
    for name, records in arms.items():
        metrics = score(records, oracle, cases)
        summaries[name] = {k: v for k, v in metrics.items() if k != "details"}
        folder = out / name
        folder.mkdir(exist_ok=True)
        run = {"created_at": manifest["created_at"], "provider": "rules" if name == "rules" else "nim",
               "model": manifest["model"] if name != "rules" else None, "workflow": name,
               "results": records, "metrics": metrics, "elapsed_seconds": round(sum(r["experiment_usage"]["logical_seconds"] for r in records), 3),
               "usage": {"requests": metrics["logical_requests"], "total_tokens": metrics["logical_tokens"]}}
        dump(folder / "run.json", run)
        dump(folder / "publications.json", [r["publication"] for r in records if r["publication"]])
        write_report(run, folder / "report.html")
    calls = client.calls if client else []
    summary = {"manifest": manifest, "cases": len(cases), "arms": summaries,
               "physical_usage": {"requests": len(calls), "tokens": sum((c.get("usage") or {}).get("total_tokens", 0) for c in calls),
                                  "errors": sum("error" in c for c in calls), "wall_seconds": round(time.perf_counter() - started, 3)},
               "paired_comparison": paired_comparison(arms["nim_single_pass"], arms["nim_conditional"], oracle, cases) if client else None,
               "stress_test": fault_experiment(cases, oracle),
               "interpretation": "Arm costs are logical standalone costs. Physical totals count shared first requests once. Tokens on timed-out calls may be unreported; no monetary price is assumed."}
    dump(out / "summary.json", summary)
    from .experiment_report import create_report
    create_report(summary, out)
    print(json.dumps({"cases": len(cases), "metrics": {k: {f: m[f] for f in ("passed", "attribute_f1", "raw_extraction_f1", "publication_precision", "publication_recall", "auto_acceptance_rate", "matching_accuracy")} for k, m in summaries.items()}, "physical_usage": summary["physical_usage"]}, indent=2))
    print(f"Experiment report: {(out / 'report.html').resolve()}")
    # Benchmark mismatches are measured outcomes, not execution failures. The
    # separate acceptance unit tests remain strict pass/fail regression checks.
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="End-to-end synthetic catalog experiments")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--out", default="data/benchmark-v2-final")
    gen.add_argument("--seed", type=int, default=20260927)
    gen.add_argument("--groups", type=int, default=24)
    run = sub.add_parser("run")
    run.add_argument("--data", default="data/benchmark-v2-final")
    run.add_argument("--out", required=True)
    run.add_argument("--split", choices=["train", "dev", "test"], default="test")
    run.add_argument("--per-stratum", type=int, default=1, help="Cases per language/scenario; zero selects the full split")
    run.add_argument("--limit", type=int, default=None, help="Smoke testing only; breaks balanced sampling")
    run.add_argument("--live", action="store_true")
    run.add_argument("--model", default=None)
    run.add_argument("--timeout", type=float, default=20)
    run.add_argument("--max-calls", type=int, default=180)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            print(json.dumps(write_benchmark(args.out, args.seed, args.groups), indent=2))
            return 0
        if args.timeout <= 0 or args.max_calls < 1 or args.per_stratum < 0 or (args.limit is not None and args.limit < 1):
            parser.error("Invalid timeout, request budget, sample size, or limit")
        return run_experiment(args)
    except (ValueError, NimError) as exc:
        print(f"Experiment stopped: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
