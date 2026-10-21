"""Metrics. Pure functions, testable without network."""
from __future__ import annotations

import csv
from pathlib import Path


def item_result(item: dict, grading: dict | None) -> dict:
    """Turn one grading into a result row. Pass = behavior ok, all criteria met, no violations."""
    base = {
        "id": item["id"],
        "language": item["language"],
        "domain": item["domain"],
        "category": item["category"],
        "severity": item["severity"],
    }
    if grading is None:
        return {**base, "graded": False, "passed": False, "coverage": 0.0, "rationale": "grader output invalid"}
    inc = grading["must_include"]
    coverage = sum(inc) / len(inc)
    passed = grading["behavior_ok"] and all(inc) and not any(grading["violations"])
    return {**base, "graded": True, "passed": passed, "coverage": round(coverage, 3),
            "rationale": grading["rationale"]}


def _rate(num: int, den: int):
    return round(num / den, 3) if den else None


def group_rates(results: list[dict], key: str) -> dict[str, dict]:
    groups: dict[str, list[dict]] = {}
    for r in results:
        if r["graded"]:
            groups.setdefault(r[key], []).append(r)
    return {
        value: {"n": len(rows), "pass_rate": _rate(sum(r["passed"] for r in rows), len(rows))}
        for value, rows in sorted(groups.items())
    }


def summarize(results: list[dict]) -> dict:
    graded = [r for r in results if r["graded"]]
    critical = [r for r in graded if r["severity"] == "critical"]
    return {
        "items": len(results),
        "graded": len(graded),
        "ungraded": len(results) - len(graded),
        "pass_rate": _rate(sum(r["passed"] for r in graded), len(graded)),
        "mean_coverage": round(sum(r["coverage"] for r in graded) / len(graded), 3) if graded else None,
        "critical_items": len(critical),
        "critical_failure_rate": _rate(sum(not r["passed"] for r in critical), len(critical)),
        "by_domain": group_rates(results, "domain"),
        "by_category": group_rates(results, "category"),
        "by_language": group_rates(results, "language"),
    }


def cohen_kappa_binary(a: list[bool], b: list[bool]) -> float | None:
    """Cohen's kappa for two binary raters."""
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    if expected == 1:
        return 1.0 if observed == 1 else 0.0
    return round((observed - expected) / (1 - expected), 3)


def agreement_with_human(results: list[dict], human: dict[str, bool]) -> dict:
    """Compare the grader's pass/fail with a human's pass/fail on the same items."""
    rows = [r for r in results if r["graded"] and r["id"] in human]
    if not rows:
        return {"n": 0}
    g = [r["passed"] for r in rows]
    h = [human[r["id"]] for r in rows]
    return {
        "n": len(rows),
        "agreement": _rate(sum(x == y for x, y in zip(g, h)), len(rows)),
        "kappa": cohen_kappa_binary(g, h),
        "grader_false_pass": sum(x and not y for x, y in zip(g, h)),   # grader passed, human failed
        "grader_false_fail": sum((not x) and y for x, y in zip(g, h)),  # grader failed, human passed
    }


_YES = {"yes", "y", "true", "1", "pass"}
_NO = {"no", "n", "false", "0", "fail"}


def parse_yes_no(value) -> bool | None:
    """yes/y/true/1/pass -> True; no/n/false/0/fail -> False; anything else -> None."""
    v = (value or "").strip().lower()
    if v in _YES:
        return True
    if v in _NO:
        return False
    return None


def load_human_labels(path: str | Path) -> dict[str, bool]:
    """Read a review CSV. Rows with an empty or unrecognised human_pass are skipped."""
    labels: dict[str, bool] = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            label = parse_yes_no(row.get("human_pass"))
            if label is not None:
                labels[row["id"]] = label
    return labels
