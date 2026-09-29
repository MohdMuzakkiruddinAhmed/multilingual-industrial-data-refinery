"""Experiment tables, standalone HTML, and optional publication-style plots."""
from html import escape
import json
from pathlib import Path

NAMES = {"rules": "Rules", "nim_single_pass": "NIM single pass", "nim_conditional": "NIM conditional"}


def fmt(value, percentage=True):
    if value is None:
        return "—"
    return f"{100 * value:.1f}%" if percentage else f"{value:,.2f}"


def charts(summary, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    arms = summary["arms"]
    keys = list(arms)
    colors = ["#52798c", "#16928a", "#c78d29"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    metrics = ["raw_extraction_f1", "attribute_f1", "matching_accuracy"]
    width = .24
    for i, name in enumerate(keys):
        axes[0, 0].bar([j + (i - (len(keys) - 1) / 2) * width for j in range(3)],
                       [100 * (arms[name][m] or 0) for m in metrics], width, label=NAMES[name], color=colors[i])
    axes[0, 0].set_xticks(range(3), ["Raw extraction F1", "Accepted-attribute F1", "Matching accuracy"])
    axes[0, 0].tick_params(axis="x", labelsize=8)
    axes[0, 0].set_ylim(0, 106)
    axes[0, 0].set_ylabel("Percent")
    axes[0, 0].set_title("Extraction and identity")
    axes[0, 0].legend(fontsize=8)
    for i, name in enumerate(keys):
        axes[0, 1].scatter(100 * arms[name]["auto_acceptance_rate"], 100 * (arms[name]["publication_precision"] or 0), s=110, color=colors[i])
        axes[0, 1].annotate(NAMES[name], (100 * arms[name]["auto_acceptance_rate"], 100 * (arms[name]["publication_precision"] or 0)), xytext=(4, -14 - i * 12), textcoords="offset points", fontsize=8)
    axes[0, 1].set_xlim(0, 100)
    axes[0, 1].set_ylim(0, 107)
    axes[0, 1].set_xlabel("Auto-acceptance coverage (%)")
    axes[0, 1].set_ylabel("Publication precision (%)")
    axes[0, 1].set_title("Precision must be read with coverage")
    labels = [NAMES[k] for k in keys]
    axes[1, 0].bar(labels, [arms[k]["logical_tokens"] for k in keys], color=colors[:len(keys)])
    axes[1, 0].set_title("Logical tokens per workflow")
    axes[1, 0].set_ylabel("Reported tokens")
    axes[1, 0].set_ylim(0, max([arms[k]["logical_tokens"] for k in keys] + [1]) * 1.15)
    for i, k in enumerate(keys):
        axes[1, 1].bar(i - .15, arms[k]["latency_seconds_p50"] or 0, .3, color="#16928a", label="p50" if i == 0 else None)
        axes[1, 1].bar(i + .15, arms[k]["latency_seconds_p95"] or 0, .3, color="#c78d29", label="p95" if i == 0 else None)
    axes[1, 1].set_xticks(range(len(keys)), labels)
    axes[1, 1].set_title("Logical per-record latency")
    axes[1, 1].set_ylabel("Seconds")
    axes[1, 1].set_ylim(bottom=0)
    axes[1, 1].legend()
    for axis in axes.flat:
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=.15)
        axis.set_axisbelow(True)
    fig.suptitle(f"Synthetic catalog experiment · {summary['cases']} cases · {summary['manifest']['split']} split", fontsize=16)
    fig.savefig(out / "comparison.png", dpi=180)
    fig.savefig(out / "comparison.svg")
    plt.close(fig)
    (out / "plot-environment.json").write_text(json.dumps({"matplotlib": matplotlib.__version__}), encoding="utf-8")
    return True


def create_report(summary, folder):
    out = Path(folder)
    arms = summary["arms"]
    keys = list(arms)
    manifest = summary["manifest"]
    metric_rows = [
        ("Exact cases", lambda m: f"{m['passed']} / {m['cases']}"),
        ("Raw extraction F1", lambda m: fmt(m["raw_extraction_f1"])),
        ("Accepted-attribute precision", lambda m: fmt(m["attribute_precision"])),
        ("Accepted-attribute recall", lambda m: fmt(m["attribute_recall"])),
        ("Accepted-attribute F1", lambda m: fmt(m["attribute_f1"])),
        ("Publication precision", lambda m: fmt(m["publication_precision"])),
        ("Publication recall", lambda m: fmt(m["publication_recall"])),
        ("Auto-acceptance coverage", lambda m: fmt(m["auto_acceptance_rate"])),
        ("Matching accuracy", lambda m: fmt(m["matching_accuracy"])),
        ("Evidence-link coverage", lambda m: fmt(m["evidence_link_coverage"])),
        ("Localization invariants", lambda m: fmt(m["localization_invariant_rate"])),
        ("Unsafe publications", lambda m: str(m["unsafe_publications"])),
        ("Unsupported accepted facts", lambda m: str(m["unsupported_accepted_attributes"])),
        ("False same-product decisions", lambda m: str(m["false_same_product_decisions"])),
        ("Logical API requests", lambda m: str(m["logical_requests"])),
        ("Logical reported tokens", lambda m: f"{m['logical_tokens']:,}"),
        ("Latency p50 / p95 (s)", lambda m: f"{fmt(m['latency_seconds_p50'], False)} / {fmt(m['latency_seconds_p95'], False)}"),
    ]
    md = ["# Synthetic catalog experiment results", "", f"{summary['cases']} cases; {manifest['split']} split; {len(manifest['groups'])} independent product-family groups.", "",
          "| Metric | " + " | ".join(NAMES[k] for k in keys) + " |", "| --- | " + " | ".join("---" for _ in keys) + " |"]
    for label, value in metric_rows:
        md.append("| " + label + " | " + " | ".join(value(arms[k]) for k in keys) + " |")
    usage = summary["physical_usage"]
    md.extend(["", f"Physical usage: {usage['requests']} requests, {usage['tokens']:,} reported tokens, {usage['errors']} request errors, {usage['wall_seconds']:.2f} seconds wall time.",
               "Logical costs include the shared first extraction in each workflow. Physical totals count it once. No dollar cost is inferred.", ""])
    paired = summary["paired_comparison"]
    if paired:
        low, high = paired["cluster_bootstrap_95_percent_interval"]
        md.extend(["## Paired comparison", "", f"Conditional minus single-pass exact-case accuracy: {100 * paired['difference']:+.2f} percentage points. Group-bootstrap 95% interval: [{100 * low:+.2f}, {100 * high:+.2f}] points.",
                   "This is a descriptive interval over a few synthetic groups, not a claim of statistical or real-world superiority.", ""])
        delta = arms["nim_conditional"]["passed"] - arms["nim_single_pass"]["passed"]
        extra = arms["nim_conditional"]["logical_requests"] - arms["nim_single_pass"]["logical_requests"]
        md.append(f"The conditional workflow produced {delta:+d} additional exactly correct records and used {extra} additional logical API requests. Advisory review does not independently authorize acceptance; extra calls do not imply better quality.")
    md.extend(["", "## Breakdowns", ""])
    tables_html = []
    for axis in ("language", "market", "scenario", "format"):
        md.extend([f"### {axis.title()}", "", "| Group | " + " | ".join(NAMES[k] + " exact cases" for k in keys) + " |", "| --- | " + " | ".join("---" for _ in keys) + " |"])
        hrows = []
        for group in sorted(arms[keys[0]]["breakdowns"][axis]):
            cells = [f"{arms[k]['breakdowns'][axis][group]['passed']} / {arms[k]['breakdowns'][axis][group]['cases']}" for k in keys]
            md.append("| " + group + " | " + " | ".join(cells) + " |")
            hrows.append("<tr><td>" + escape(group) + "</td>" + "".join("<td>" + escape(c) + "</td>" for c in cells) + "</tr>")
        md.append("")
        tables_html.append(f"<details><summary>{axis.title()} breakdown</summary><table><thead><tr><th>{axis.title()}</th>" + "".join(f"<th>{NAMES[k]}</th>" for k in keys) + "</tr></thead><tbody>" + "".join(hrows) + "</tbody></table></details>")
    stress = summary["stress_test"]["counts"]
    md.extend(["## Injected-fault control experiment", "", f"{stress.get('injected_claims', 0)} deliberately corrupted proposals: {stress.get('guarded_wrong_acceptances', 0)} accepted by the evidence gate; {stress.get('unchecked_wrong_acceptances', 0)} copied by the simulated no-check comparator.",
               "This is a deterministic fault-injection experiment, not a measured NIM hallucination rate. The unchecked comparator never publishes.", "",
               "## Limitations and metric definitions", "",
               "- Raw extraction F1 compares deduplicated source/field/value/unit tuples with the independent source-level oracle. Contradictory but explicitly stated facts are valid raw extractions.",
               "- Accepted-attribute F1 compares canonical field/value pairs with conflict-resolved ground truth; missing facts count as false negatives.",
               "- Publication precision measures correct publishability decisions among approvals. Accepted-record correctness additionally checks all attributes and identity.",
               "- Publication recall measures approved records among all ideally publishable records. Narrative records remain in the denominator even when the narrow verifier cannot accept them.",
               "- Provider failures stay in denominators; successful reruns never replace failed attempts in this report.",
               "- Evidence-link coverage is structural traceability. It is not independent proof of source truth.",
               "- Localization is controlled terminology rendering and value preservation, not a human-rated translation-quality benchmark.",
               "- Splits separate product families; they share rendering templates. No real data, trained model, or independently validated bilingual gold labels are claimed.",
               "- Synthetic test families are held apart from development. Model prompts and evaluation configuration are saved in the pre-run manifest; the oracle never enters model requests.",
               "", "## Artifacts", "", "- `summary.json`: machine-readable metrics, counts, breakdowns, and paired comparison.", "- `manifest.json` / `protocol.json`: frozen inputs, source hashes, prompts, and experimental design.",
               "- `calls.json`: actual NIM request/response audit when live inference is enabled.", "- Per-workflow `run.json`, `report.html`, and `publications.json`.", "- `comparison.png` and `comparison.svg`: standard Matplotlib figures (when installed)."])
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    has_plot = charts(summary, out)
    table = "<table><thead><tr><th>Metric</th>" + "".join(f"<th>{NAMES[k]}</th>" for k in keys) + "</tr></thead><tbody>"
    for label, value in metric_rows:
        table += "<tr><td>" + escape(label) + "</td>" + "".join("<td>" + escape(value(arms[k])) + "</td>" for k in keys) + "</tr>"
    table += "</tbody></table>"
    links = "".join(f'<a href="{k}/report.html">Inspect {NAMES[k]} cases →</a>' for k in keys)
    pairing = ""
    if paired:
        pairing = f"<p>Conditional − single pass: <strong>{100 * paired['difference']:+.2f} percentage points</strong> in exact-case accuracy. Descriptive group-bootstrap interval [{100 * low:+.2f}, {100 * high:+.2f}].</p>"
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Refinery · Experiment results</title>
<style>body{{margin:0;background:#f1f6f6;color:#163341;font:15px/1.6 system-ui,sans-serif}}header{{background:#12313c;color:white;padding:36px max(24px,calc((100vw - 1140px)/2));border-bottom:5px solid #66cdb6}}h1{{font-weight:600;margin:8px 0;font-size:34px}}header small{{letter-spacing:2px;color:#98dace}}main{{max-width:1140px;margin:24px auto;padding:0 20px}}.card{{background:white;border:1px solid #d6e3e5;border-radius:10px;padding:24px;margin-bottom:20px}}.links{{display:flex;gap:15px;flex-wrap:wrap}}a{{color:#087b70;text-decoration:none}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:10px 12px;border-bottom:1px solid #e0e9ea;text-align:left}}th{{color:#5b727b;font-size:11px;text-transform:uppercase}}td:not(:first-child){{font-variant-numeric:tabular-nums;font-weight:600}}img{{width:100%;height:auto}}summary{{padding:15px 0;cursor:pointer;font-weight:650}}.note{{color:#607680;font-size:13px}}h2{{font-size:21px}}.scroll{{overflow:auto}}@media(max-width:700px){{h1{{font-size:27px}}.card{{padding:14px}}td,th{{padding:8px 6px}}}}</style></head>
<body><header><small>MULTILINGUAL INDUSTRIAL DATA REFINERY / EXPERIMENT V2</small><h1>Measured outcomes, visible limits.</h1><div>{summary['cases']} cases · {len(manifest['groups'])} product families · {escape(manifest['split'])} split · {escape(manifest['model'] or 'offline baseline')}</div></header>
<main><div class="card links">{links}<a href="RESULTS.md">Detailed report →</a><a href="summary.json">Metrics JSON →</a></div>
<div class="card scroll"><h2>Workflow comparison</h2>{table}{pairing}<p class="note">Physical total: {usage['requests']} API requests · {usage['tokens']:,} reported tokens · {usage['errors']} request errors · {usage['wall_seconds']:.2f}s. Both NIM arms share their first response; their logical costs each include it.</p></div>
{('<div class="card"><img src="comparison.png" alt="Comparison of extraction quality, acceptance coverage, token usage, and latency"></div>') if has_plot else ''}
<div class="card"><h2>Where each workflow succeeds and fails</h2>{''.join(tables_html)}</div>
<div class="card"><h2>Fault-injection control</h2><p>{stress.get('injected_claims', 0)} corrupted proposals. <strong>{stress.get('guarded_wrong_acceptances', 0)} unsafe acceptances</strong> with the evidence gate. The simulated unchecked comparator accepts {stress.get('unchecked_wrong_acceptances', 0)}.</p><p class="note">A controlled intervention, not an estimate of model hallucination. No unchecked output is published.</p></div>
<div class="card"><h2>How to interpret these results</h2><p>Read correctness together with coverage. A system that rejects difficult records may preserve precision while missing useful facts. Narrative descriptions deliberately remain in the benchmark, exposing the current verifier's coverage limit.</p><p class="note">Synthetic templates; group-disjoint splits; no real-world accuracy claim. Controlled market rendering does not measure translation quality. HTTP failures remain in the results. Few-group bootstrap intervals are descriptive only.</p></div></main></body></html>'''
    (out / "report.html").write_text(html, encoding="utf-8")
