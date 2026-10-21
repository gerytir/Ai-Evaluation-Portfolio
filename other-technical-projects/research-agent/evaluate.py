"""Evaluate the research agent on eval_set.json.

Usage:
    python evaluate.py                # all questions
    python evaluate.py --limit 3      # first 3 only (quick trial)

Writes to output/:
  results.json         full data for every question
  REPORT.md            metrics table, ready to paste into the portfolio
  manual_review.csv    claims to review by hand (fill the human_verdict column)
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import anthropic

from agent import MODEL, run_research
from metrics import is_refusal, keyword_coverage, summarize
from verify import judge_claim

HERE = Path(__file__).parent
OUT = HERE / "output"


def evaluate(limit: int | None = None) -> tuple[list[dict], dict]:
    client = anthropic.Anthropic()
    items = json.loads((HERE / "eval_set.json").read_text(encoding="utf-8"))
    if limit:
        items = items[:limit]

    rows: list[dict] = []
    for item in items:
        print(f"[{item['id']}] {item['question']}")
        result = run_research(item["question"], client=client)
        judged = []
        for claim in result.claims:
            verdict = judge_claim(claim.text, claim.sources, client=client)
            judged.append(
                {
                    "text": claim.text,
                    "sources": claim.sources,
                    "verdict": verdict["verdict"],
                    "reason": verdict["reason"],
                }
            )
        rows.append(
            {
                "id": item["id"],
                "question": item["question"],
                "answer": result.answer,
                "claims": judged,
                "verdicts": [j["verdict"] for j in judged],
                "n_uncited": len(result.uncited_text),
                "uncited_text": result.uncited_text,
                "n_searches": len(result.searches),
                "coverage": keyword_coverage(result.answer, item["expected_keywords"]),
                "expect_refusal": item["expect_refusal"],
                "refused": is_refusal(result.answer),
            }
        )
    return rows, summarize(rows)


def write_outputs(rows: list[dict], summary: dict) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "results.json").write_text(
        json.dumps({"model": MODEL, "summary": summary, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (OUT / "manual_review.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "claim", "url", "cited_passage", "judge_verdict", "human_verdict"])
        for r in rows:
            for c in r["claims"]:
                src = c["sources"][0]
                w.writerow([r["id"], c["text"], src["url"], src["cited_text"], c["verdict"], ""])

    def pct(x):
        return "n/a" if x is None else f"{x:.0%}"

    lines = [
        "# Evaluation report - research agent with citations",
        "",
        f"Model: `{MODEL}` - questions: {summary['questions']}",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Cited / uncited claims | {summary['cited_claims']} / {summary['uncited_claims']} |",
        f"| Citation rate | {pct(summary['citation_rate'])} |",
        f"| Claims supported by the source | {pct(summary['supported_rate'])} |",
        f"| Claims partially supported | {pct(summary['partial_rate'])} |",
        f"| Claims not supported | {pct(summary['unsupported_rate'])} |",
        f"| Expected keyword coverage | {pct(summary['keyword_coverage'])} |",
        f"| Trap questions handled (correct refusal) | {pct(summary['traps_handled'])} |",
        f"| Average searches per question | {summary['avg_searches']} |",
        "",
        "## Per-question detail",
        "",
        "| ID | Cited | Uncited | Supported | Unsupported | Refused |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        v = r["verdicts"]
        refusal = "yes" if r["refused"] else "no"
        lines.append(
            f"| {r['id']} | {len(v)} | {r['n_uncited']} | {v.count('supported')} | "
            f"{v.count('unsupported')} | {refusal} |"
        )
    lines += [
        "",
        "## Known limits of the measurement",
        "- The judge is an LLM: compare it with human judgment (column `human_verdict` in `manual_review.csv`).",
        "- Refusal on trap questions is detected with keywords and can give false positives or negatives.",
        "- The judge sees only the cited passage: it checks that the source says what the agent claims, not that the source is true.",
        "- Answers depend on the web results of the moment: two runs can differ.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    rows, summary = evaluate(args.limit)
    write_outputs(rows, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Output in {OUT}")
