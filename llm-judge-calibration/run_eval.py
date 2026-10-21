"""Run the judge on pairs.json and measure how far it can be trusted.

Usage:
    python run_eval.py              # all pairs
    python run_eval.py --limit 3    # quick trial

Writes to output/: results.json and REPORT.md.

Important: the `gold` labels in pairs.json were written by the project author.
Re-label them yourself, blind (before looking at the judge output), then run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import anthropic

from judge import MODEL, judge_pair
from metrics import summarize

HERE = Path(__file__).parent
OUT = HERE / "output"


def run(limit: int | None = None, client=None) -> tuple[list[dict], dict, dict]:
    client = client or anthropic.Anthropic()
    pairs = json.loads((HERE / "pairs.json").read_text(encoding="utf-8"))
    if limit:
        pairs = pairs[:limit]
    gold = {p["id"]: p["gold"] for p in pairs}
    rows = []
    for p in pairs:
        print(f"[{p['id']}] {p['kind']}")
        rows.append(judge_pair(p, client))
    return rows, summarize(rows, gold), gold


def write_outputs(rows: list[dict], summary: dict, gold: dict) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "results.json").write_text(
        json.dumps({"model": MODEL, "summary": summary, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    def f(x):
        return "n/a" if x is None else str(x)

    lines = [
        "# Evaluation report - LLM-as-judge",
        "",
        f"Judge model: `{MODEL}` - pairs: {summary['pairs']} (judged: {summary['judged']})",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Agreement with gold, original order | {f(summary['agreement_original_order'])} |",
        f"| Agreement with gold, final verdict (both orders) | {f(summary['agreement_final_verdict'])} |",
        f"| Cohen's kappa, final verdict | {f(summary['kappa_final_verdict'])} |",
        f"| Swap consistency (same preference in both orders) | {f(summary['swap_consistency'])} |",
        f"| First-slot bias (0.5 = none) | {f(summary['first_slot_bias'])} |",
        f"| Mean rubric score gap for the gold winner | {f(summary['mean_score_gap_for_gold_winner'])} |",
        "",
        "## Per-pair detail",
        "",
        "| ID | Gold | Original order | Swapped order | Final |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        o = r["original"]["preference"] if r["original"] else "invalid"
        s = r["swapped"]["preference"] if r["swapped"] else "invalid"
        lines.append(f"| {r['id']} | {gold[r['id']]} | {o} | {s} | {r['final']} |")
    lines += [
        "",
        "## How to read it",
        "- Kappa corrects agreement for chance. Around 0.6 to 0.8 is usually read as substantial, but with 9 pairs it is only indicative.",
        "- Low swap consistency or a first-slot bias far from 0.5 means the judge is influenced by the position of the answer.",
        "- Inspect every disagreement with the gold label: either the judge is wrong or the label is debatable. Both are findings.",
        "",
        "## Known limits",
        "- Gold labels were written by the project author. Re-label them blind before trusting the numbers.",
        "- 9 pairs is a very small sample. Extend it before drawing conclusions.",
        "- Most pairs have one clearly better response; real evaluation work is mostly in the harder close calls.",
        "- The judge model can be the same family as the models it evaluates, which may favour its own style.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    rows, summary, gold = run(args.limit)
    write_outputs(rows, summary, gold)
    print(json.dumps(summary, indent=2))
    print(f"Output in {OUT}")
