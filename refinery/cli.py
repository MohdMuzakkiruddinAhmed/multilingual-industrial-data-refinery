import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from . import __version__
from .engine import refine_case, digest
from .evaluation import evaluate
from .nim import NimClient, NimError, EXTRACT_SYSTEM, REVIEW_SYSTEM
from .report import write_report
from .synthetic import write_dataset


def main(argv=None):
    parser = argparse.ArgumentParser(description="Synthetic multilingual industrial catalog refinery")
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate", help="Write synthetic source records and a separate oracle")
    generate.add_argument("--out", default="data")
    execute = sub.add_parser("run", help="Run the synthetic benchmark and build an HTML review dashboard")
    execute.add_argument("--provider", choices=["rules", "nim"], default="rules")
    execute.add_argument("--data", default="data")
    execute.add_argument("--out", default=None)
    execute.add_argument("--case", action="append", help="Run only named case(s)")
    execute.add_argument("--model", default=None)
    execute.add_argument("--max-calls", type=int, default=50)
    execute.add_argument("--timeout", type=float, default=30, help="Network timeout in seconds per request")
    execute.add_argument("--no-review", action="store_true", help="Skip advisory NIM review; deterministic checks still apply")
    args = parser.parse_args(argv)
    if args.command == "generate":
        inputs, _ = write_dataset(args.out)
        print(f"Wrote {len(inputs['cases'])} synthetic cases to {args.out}")
        return 0
    data_path = Path(args.data)
    if not (data_path / "sources.json").exists():
        write_dataset(data_path)
    inputs = json.loads((data_path / "sources.json").read_text(encoding="utf-8"))
    expected = json.loads((data_path / "expected.json").read_text(encoding="utf-8"))
    if not inputs.get("synthetic") or any(not s.get("synthetic") for c in inputs["cases"] for s in c["sources"]):
        parser.error("This benchmark command accepts explicitly synthetic data only")
    cases = [c for c in inputs["cases"] if not args.case or c["id"] in args.case]
    if not cases or (args.case and set(args.case) - {c["id"] for c in cases}):
        parser.error("Unknown case or no cases selected")
    try:
        if args.timeout <= 0 or args.max_calls < 1:
            parser.error("Timeout and request budget must be positive")
        client = NimClient(model=args.model, max_calls=args.max_calls, timeout=args.timeout) if args.provider == "nim" else None
    except NimError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    out = Path(args.out or f"outputs/{args.provider}-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    out.mkdir(parents=True, exist_ok=True)
    results = []
    started = time.monotonic()
    for index, case in enumerate(cases, 1):
        record = refine_case(case, inputs["catalog"], client, review=not args.no_review)
        results.append(record)
        print(f"[{index}/{len(cases)}] {case['id']}: {record['state']} ({len(record['attributes'])} attributes)", flush=True)
        # Recoverable checkpoint after each case; no credentials or reasoning traces.
        (out / "checkpoint.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        if client:
            (out / "calls.json").write_text(json.dumps(client.calls, ensure_ascii=False, indent=2), encoding="utf-8")
    calls = client.calls if client else []
    run = {"version": __version__, "created_at": datetime.now(timezone.utc).isoformat(),
           "provider": args.provider, "model": client.model if client else None,
           "base_url": client.base_url if client else None, "python": platform.python_version(),
           "dataset_version": inputs["version"], "dataset_sha256": digest(inputs),
           "prompt_sha256": digest({"extract": EXTRACT_SYSTEM, "review": REVIEW_SYSTEM}),
           "elapsed_seconds": round(time.monotonic() - started, 3), "results": results,
           "metrics": evaluate(results, expected),
           "usage": {"requests": len(calls), "total_tokens": sum((c.get("usage") or {}).get("total_tokens", 0) for c in calls),
                     "api_errors": sum("error" in c for c in calls),
                     "unrecovered_errors": sum(any(i["code"] == "provider_error" for i in r["issues"]) or bool((r["advisory_review"] or {}).get("error")) for r in results)}}
    (out / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "publications.json").write_text(json.dumps([r["publication"] for r in results if r["publication"]], ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(run, out / "report.html")
    print(json.dumps({k: v for k, v in run["metrics"].items() if k not in ("details", "by_language", "by_market")}, indent=2))
    print(f"Report: {(out / 'report.html').resolve()}")
    print(f"Requests: {run['usage']['requests']}; tokens: {run['usage']['total_tokens']}; API errors: {run['usage']['api_errors']}")
    return 0 if run["metrics"]["passed"] == len(cases) and not run["usage"]["unrecovered_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
