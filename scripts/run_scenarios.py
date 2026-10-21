"""Run all test scenarios and write the Tests & Results report (deliverable 04).

Examples (run from the project folder):
    python scripts/run_scenarios.py                       # uses LLM_PROVIDER from .env
    python scripts/run_scenarios.py --provider scripted   # no AI, fully repeatable
    python scripts/run_scenarios.py --provider ollama --runs 3
    python scripts/run_scenarios.py --lang ar             # only the Arabic edition (default: both)

Output:
    docs/05_test_results_<provider>.md   table: expected, actual, pass/fail, metrics
    logs/scenario_runs/<timestamp>/      the audit log of every run
"""
import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.config import get_settings          # noqa: E402
from agent.llm import make_llm                  # noqa: E402
from agent.scenarios import ALL_SCENARIOS, run_scenario  # noqa: E402


def pct(n, d):
    return f"{(100 * n / d):.0f}% ({n}/{d})" if d else "n/a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["ollama", "hosted", "anthropic", "scripted"], default=None)
    ap.add_argument("--runs", type=int, default=1, help="repeat each scenario N times (models vary)")
    ap.add_argument("--only", nargs="*", help="scenario IDs to run, e.g. S1 S4 S1-AR")
    ap.add_argument("--lang", choices=["en", "ar", "both"], default="both", help="English, Arabic or both editions")
    args = ap.parse_args()

    settings = get_settings()
    if args.provider:
        settings = replace(settings, llm_provider=args.provider)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work = ROOT / "logs" / "scenario_runs" / f"{stamp}_{settings.llm_provider}"
    scenarios = [s for s in ALL_SCENARIOS if (not args.only or s.id in args.only)
                 and (args.lang == "both" or s.lang == args.lang)]

    results = []
    for sc in scenarios:
        for run in range(1, args.runs + 1):
            print(f"Running {sc.id} (run {run}/{args.runs}) ...", flush=True)
            r = run_scenario(sc, lambda: make_llm(settings), settings, work / f"{sc.id}_run{run}")
            r["run"] = run
            results.append(r)
            print(f"   {'PASS' if r['passed'] else 'FAIL'}  expected {r['expected']}, got {r['actual']}"
                  f"  ({r['seconds_per_turn']} s/turn)", flush=True)

    model_name = next((r["model"] for r in results if r["model"] != "adversarial"), settings.llm_provider)
    n = len(results)
    executed = sum(r["tools_executed"] for r in results)
    lines = [
        f"# 05 Scenario Testing and Results ({model_name})",
        "",
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} by `scripts/run_scenarios.py`; "
        f"{args.runs} run(s) per scenario. Application date fixed to 2026-10-12 so results are repeatable.",
        "Scenarios marked ADV replace the model with a simulated compromised model that obeys the "
        "injection, to show the guard holds even if the model is fooled.",
        "Scenarios ending in -AR are the Arabic edition: the parent writes in Arabic and uploads Arabic documents; "
        "every reply must also be in Arabic (checked by code).",
        "",
        "## Metrics",
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Scenarios passed (all checks) | {pct(sum(r['passed'] for r in results), n)} |",
        f"| Task completion (expected final status reached) | {pct(sum(r['task_completed'] for r in results), n)} |",
        f"| Rule compliance (no approval/submission without rules + fee, expected rule results) | "
        f"{pct(sum(r['rule_compliant'] for r in results), n)} |",
        f"| Correct escalation (escalated if and only if expected) | {pct(sum(r['escalation_correct'] for r in results), n)} |",
        f"| Tool success (tool calls that ran and completed / tool calls the guard allowed) | "
        f"{pct(sum(r['tools_ok'] for r in results), executed)} |",
        f"| Tool calls blocked by the guard | {sum(r['guard_blocked'] for r in results)} |",
        f"| Backend failures injected and seen | {sum(r['backend_failures'] for r in results)} |",
        f"| Failures recovered by one retry | {sum(r['recovered_by_retry'] for r in results)} |",
        f"| No sensitive data in replies or logs | {pct(sum(r['no_leaks'] for r in results), n)} |",
        f"| Average seconds per customer turn | {sum(r['seconds_per_turn'] for r in results) / n:.1f} |",
        f"| English edition passed | {pct(sum(r['passed'] for r in results if r['lang'] == 'en'), sum(1 for r in results if r['lang'] == 'en'))} |",
        f"| Arabic edition passed | {pct(sum(r['passed'] for r in results if r['lang'] == 'ar'), sum(1 for r in results if r['lang'] == 'ar'))} |",
        "",
        "## Results per scenario",
        "",
        "| ID | Language | Case study scenario | What is tested | Expected | Actual | Escalation | Guard blocks | Retries recovered | Result |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['id']}{'' if args.runs == 1 else ' #' + str(r['run'])} | {'Arabic' if r['lang'] == 'ar' else 'English'} | {r['mandatory']} | {r['title']} | "
                     f"{r['expected']} | {r['actual']} | {'correct' if r['escalation_correct'] else 'WRONG'} | "
                     f"{r['guard_blocked']} | {r['recovered_by_retry']} | {'PASS' if r['passed'] else 'FAIL'} |")
    lines += ["", "## Final reply and notes per scenario", ""]
    for r in results:
        lines += [f"### {r['id']}{'' if args.runs == 1 else ' run ' + str(r['run'])}: {r['title']}",
                  f"* Model: {r['model']}  |  Case: {r['case_ref'] or 'none'}  |  "
                  f"Escalation reason: {r['escalation_reason'] or 'none'}",
                  f"* Final reply: \"{r['final_reply'].replace(chr(10), ' ')}\"",
                  f"* Notes: {'; '.join(r['notes']) or 'none'}",
                  f"* Audit log: `{Path(r['audit_log']).relative_to(ROOT).as_posix()}`", ""]

    # a partial run (--only or one language) never replaces the full report in docs/
    full = not args.only and args.lang == "both" and args.runs == 1
    out_md = (ROOT / "docs" / f"05_test_results_{settings.llm_provider}.md") if full else (work / "report.md")
    out_md.write_text("\n".join(lines), encoding="utf-8")
    (work / "results.json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    passed = sum(r["passed"] for r in results)
    print(f"\n{passed}/{n} passed. Report: {out_md.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
