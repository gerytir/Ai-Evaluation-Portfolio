"""Tests for manual mode (no API key)."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from eval_lab import cli, manual, schema  # noqa: E402
from eval_lab.metrics import parse_yes_no  # noqa: E402

DATASET = ROOT / "datasets" / "italian_core.json"


def test_parse_yes_no():
    assert parse_yes_no(" YES ") is True
    assert parse_yes_no("no") is False
    assert parse_yes_no("") is None
    assert parse_yes_no(None) is None
    assert parse_yes_no("maybe") is None


def test_worksheet_roundtrip_keeps_accents_and_guillemets(tmp_path):
    items = schema.load_dataset(DATASET)
    path = tmp_path / "ws.csv"
    manual.write_worksheet(items[:3], path)
    rows = manual.read_worksheet(path)
    assert [r["id"] for r in rows] == ["it01", "it02", "it03"]
    assert "«" in rows[0]["prompt"]
    assert set(manual.COLUMNS) <= set(rows[0])


def test_build_manual_skips_unlabelled_rows():
    items = schema.load_dataset(DATASET)[:3]
    rows = [
        {"id": "it01", "response": "ok", "human_pass": "yes", "human_note": ""},
        {"id": "it02", "response": "bad", "human_pass": "no", "human_note": "used the wrong form"},
        {"id": "it03", "response": "", "human_pass": "", "human_note": ""},
    ]
    responses, gradings = manual.build_manual(items, rows)
    assert set(gradings) == {"it01", "it02"}
    assert gradings["it01"]["behavior_ok"] is True
    assert gradings["it02"]["rationale"] == "used the wrong form"
    assert len(gradings["it01"]["must_include"]) == len(items[0]["must_include"])


def test_cli_worksheet_and_manual_report(tmp_path, capsys):
    ws = tmp_path / "ws.csv"
    assert cli.main(["worksheet", str(DATASET), "--out", str(ws), "--limit", "4"]) == 0

    # Without labels the report refuses to run.
    assert cli.main(["manual-report", str(DATASET), str(ws), "--model", "m", "--out-dir", str(tmp_path / "o")]) == 1

    rows = list(csv.DictReader(ws.open(encoding="utf-8-sig")))
    for r, label in zip(rows, ["yes", "yes", "no", "yes"]):
        r["response"] = "some answer"
        r["human_pass"] = label
    with ws.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=manual.COLUMNS)
        w.writeheader()
        w.writerows(rows)

    out = tmp_path / "out"
    assert cli.main(["manual-report", str(DATASET), str(ws), "--model", "Chatbot X", "--out-dir", str(out)]) == 0
    data = json.loads((out / "results.json").read_text(encoding="utf-8"))
    assert data["summary"]["graded"] == 4
    assert data["summary"]["pass_rate"] == 0.75
    text = (out / "REPORT.md").read_text(encoding="utf-8")
    assert "Labelling mode: **manual**" in text
    assert "Agreement between grader" not in text
    assert "Mean checklist coverage" not in text
