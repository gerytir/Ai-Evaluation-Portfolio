"""Write the report files: results.json, REPORT.md and human_review.csv."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .metrics import agreement_with_human, item_result, summarize


def _pct(x):
    return "n/a" if x is None else f"{x:.0%}"


def build_results(items: list[dict], gradings: dict[str, dict | None]) -> list[dict]:
    return [item_result(i, gradings[i["id"]]) for i in items if i["id"] in gradings]


def write_report(items: list[dict], responses: dict[str, str], gradings: dict[str, dict | None],
                 out_dir: str | Path, dataset_name: str, target_model: str,
                 human: dict[str, bool] | None = None, manual: bool = False,
                 grader: str | None = None) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    by_id = {i["id"]: i for i in items}
    results = build_results(items, gradings)
    summary = summarize(results)
    agree = agreement_with_human(results, human) if human else None

    (out / "results.json").write_text(
        json.dumps({"dataset": dataset_name, "target_model": target_model, "summary": summary,
                    "human_agreement": agree, "results": results, "gradings": gradings},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (out / "human_review.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "domain", "category", "prompt", "response", "grader_pass",
                    "grader_rationale", "human_pass", "human_note"])
        for r in results:
            it = by_id[r["id"]]
            w.writerow([r["id"], r["domain"], r["category"], it["prompt"], responses.get(r["id"], ""),
                        "yes" if r["passed"] else "no", r["rationale"], "", ""])

    lines = [
        f"# Evaluation report - {dataset_name}",
        "",
        f"Model under test: `{target_model}` - items graded: {summary['graded']} of {summary['items']}",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Overall pass rate | {_pct(summary['pass_rate'])} |",
        *([] if manual else [f"| Mean checklist coverage | {_pct(summary['mean_coverage'])} |"]),
        f"| Critical items / critical failure rate | {summary['critical_items']} / {_pct(summary['critical_failure_rate'])} |",
        *([] if manual else [f"| Ungraded (invalid grader output) | {summary['ungraded']} |"]),
        "",
    ]
    if manual:
        lines.insert(3, "Labelling mode: **manual**. Every pass/fail comes from a human reviewer; no automatic grader was used.")
        lines.insert(4, "")
    elif grader:
        lines.insert(3, f"Grader: {grader}")
        lines.insert(4, "")
    for title, key in (("Pass rate by domain", "by_domain"), ("Pass rate by category", "by_category"),
                       ("Pass rate by language", "by_language")):
        lines += [f"## {title}", "", "| Group | Items | Pass rate |", "|---|---|---|"]
        for name, g in summary[key].items():
            lines.append(f"| {name} | {g['n']} | {_pct(g['pass_rate'])} |")
        lines.append("")

    failed = [r for r in results if r["graded"] and not r["passed"]]
    lines += ["## Failed items", "", "| ID | Severity | Category | Grader rationale |", "|---|---|---|---|"]
    for r in failed:
        lines.append(f"| {r['id']} | {r['severity']} | {r['category']} | {r['rationale'].replace('|', '/')} |")
    if not failed:
        lines.append("| - | - | - | none |")
    lines.append("")

    if not manual:
        lines += ["## Agreement between grader and human review", ""]
        if agree and agree["n"]:
            lines += [
                "| Metric | Value |", "|---|---|",
                f"| Items compared | {agree['n']} |",
                f"| Agreement | {_pct(agree['agreement'])} |",
                f"| Cohen's kappa | {agree['kappa']} |",
                f"| Grader passed, human failed (dangerous) | {agree['grader_false_pass']} |",
                f"| Grader failed, human passed | {agree['grader_false_fail']} |",
            ]
        else:
            lines.append("No human labels yet. Fill the `human_pass` column of `human_review.csv` (yes/no) and run the report again with `--human`.")
    lines += [
        "",
        "## Known limits",
        "- Checklists were drafted by the project author. Review and correct them before relying on the numbers.",
        *(["- Labels come from one human reviewer. A second reviewer would allow agreement between humans to be measured."]
          if manual else
          ["- The grader applies the checklist literally and can misjudge borderline wording; the human review measures how often."]),
        "- A small set gives indicative results, not statistically robust ones.",
        "- Results describe one model, one prompt wording and one run.",
    ]
    (out / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"summary": summary, "human_agreement": agree}
