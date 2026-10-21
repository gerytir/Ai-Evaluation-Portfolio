"""Evaluate the triage agent on tickets.json.

Usage:
    python evaluate.py              # all tickets
    python evaluate.py --limit 5    # quick trial

Writes to output/: results.json, REPORT.md (metrics + errors to analyse).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import anthropic

from metrics import confusion_matrix, summarize
from triage import MODEL, triage_ticket

HERE = Path(__file__).parent
OUT = HERE / "output"


def run(limit: int | None = None, client=None) -> tuple[list[dict], dict]:
    client = client or anthropic.Anthropic()
    tickets = json.loads((HERE / "tickets.json").read_text(encoding="utf-8"))
    if limit:
        tickets = tickets[:limit]
    rows = []
    for t in tickets:
        print(f"[{t['id']}] {t['text'][:70]!r}")
        rows.append({**t, "pred": triage_ticket(t["text"], client=client)})
    return rows, summarize(rows)


def write_outputs(rows: list[dict], summary: dict) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "results.json").write_text(
        json.dumps({"model": MODEL, "summary": summary, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    def pct(x):
        return "n/a" if x is None else f"{x:.0%}"

    lines = [
        "# Evaluation report - IT helpdesk triage agent",
        "",
        f"Model: `{MODEL}` - tickets: {summary['tickets']}",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Category accuracy | {pct(summary['category_accuracy'])} |",
        f"| Priority exact / within one level | {pct(summary['priority_exact'])} / {pct(summary['priority_within_one'])} |",
        f"| Escalation recall (tickets that need a human) | {pct(summary['escalation_recall'])} |",
        f"| False escalation rate | {pct(summary['false_escalation_rate'])} |",
        f"| Security tickets escalated | {pct(summary['security_escalation_recall'])} |",
        f"| Prompt-injection resistance | {pct(summary['injection_resistance'])} |",
        f"| Valid JSON on first try | {pct(summary['valid_first_try'])} |",
        f"| Guardrail interventions | {summary['guardrail_triggers']} |",
        "",
        "## Errors to analyse",
        "",
        "| ID | Tag | Gold | Predicted | Flags |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        p = r["pred"]
        wrong = (
            p["category"] != r["gold_category"]
            or p["priority"] != r["gold_priority"]
            or p["needs_human"] != r["gold_needs_human"]
        )
        if wrong:
            gold = f"{r['gold_category']} / {r['gold_priority']} / human={r['gold_needs_human']}"
            pred = f"{p['category']} / {p['priority']} / human={p['needs_human']}"
            lines.append(f"| {r['id']} | {r['tag']} | {gold} | {pred} | {', '.join(p.get('flags', [])) or '-'} |")
    lines += [
        "",
        "## Confusion matrix (gold -> predicted)",
        "",
        "```json",
        json.dumps(confusion_matrix(rows), indent=2),
        "```",
        "",
        "## Known limits",
        "- Gold labels were written by the project author. Re-label blind with your own policy before trusting the numbers.",
        "- 22 synthetic tickets is a small sample: indicative, not statistically robust.",
        "- The injection test uses one canary string; a real attacker has many more options.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    rows, summary = run(args.limit)
    write_outputs(rows, summary)
    print(json.dumps(summary, indent=2))
    print(f"Output in {OUT}")
