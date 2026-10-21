"""Manual mode: no API key, no cost.

1. `worksheet` writes a CSV with every prompt and its checklist.
2. You paste each prompt into a chatbot (a fresh chat per prompt), paste the answer into
   the `response` column and fill `human_pass` with yes/no (and a note for every no).
3. `manual-report` computes the same tables as the automatic mode, from your labels.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .metrics import parse_yes_no

COLUMNS = ["id", "domain", "category", "expected_behavior", "prompt", "must_include",
           "must_avoid", "response", "human_pass", "human_note"]


def write_worksheet(items: list[dict], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so that Excel opens accents and « » correctly
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for i in items:
            w.writerow([i["id"], i["domain"], i["category"], i["expected_behavior"], i["prompt"],
                        " | ".join(i["must_include"]), " | ".join(i["must_avoid"]), "", "", ""])


def read_worksheet(path: str | Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_manual(items: list[dict], rows: list[dict]) -> tuple[dict[str, str], dict[str, dict]]:
    """Turn labelled worksheet rows into (responses, gradings). Unlabelled rows are skipped.

    A human pass means every criterion was met. A human fail records the note as rationale.
    """
    by_id = {r["id"]: r for r in rows}
    responses: dict[str, str] = {}
    gradings: dict[str, dict] = {}
    for item in items:
        row = by_id.get(item["id"])
        if not row:
            continue
        label = parse_yes_no(row.get("human_pass"))
        if label is None:
            continue
        responses[item["id"]] = row.get("response") or ""
        gradings[item["id"]] = {
            "must_include": [label] * len(item["must_include"]),
            "violations": [False] * len(item["must_avoid"]),
            "behavior_ok": label,
            "rationale": (row.get("human_note") or "").strip() or ("Passed human review" if label else "Failed human review"),
        }
    return responses, gradings
