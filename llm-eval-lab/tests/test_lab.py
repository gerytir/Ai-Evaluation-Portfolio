"""Offline tests: no network, no API key. Run with `pytest` from the project folder."""
import csv
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from eval_lab import cli, grade, metrics, report, schema  # noqa: E402
from eval_lab.generate import generate_responses  # noqa: E402

DATASETS = sorted((ROOT / "datasets").glob("*.json"))


def make_item(**over):
    base = {
        "id": "x1", "language": "en", "domain": "it", "category": "factual", "severity": "normal",
        "expected_behavior": "answer", "prompt": "What does DNS do?",
        "must_include": ["Says DNS maps names to IP addresses"],
        "must_avoid": ["Says DNS encrypts traffic"],
        "source_note": "RFC 1034",
    }
    base.update(over)
    return base


class FakeClient:
    """Plays both the model under test and the grader."""

    def __init__(self, items, grader_pass=True):
        self.items = items
        self.grader_pass = grader_pass
        self.messages = self

    def create(self, **kw):
        content = kw["messages"][0]["content"]
        if "strict, literal grader" in content:
            item = next(i for i in self.items if i["prompt"] in content)
            out = {
                "must_include": [self.grader_pass] * len(item["must_include"]),
                "violations": [False] * len(item["must_avoid"]),
                "behavior_ok": self.grader_pass,
                "rationale": "ok" if self.grader_pass else "fails the checklist",
            }
            text = json.dumps(out)
        else:
            text = "A model response."
        return NS(content=[NS(type="text", text=text)])


# ---- schema ---------------------------------------------------------------

def test_real_datasets_are_valid():
    assert len(DATASETS) == 2
    for path in DATASETS:
        items = schema.load_dataset(path)
        assert len(items) >= 30


def test_dataset_composition():
    it = schema.load_dataset(ROOT / "datasets" / "italian_core.json")
    en = schema.load_dataset(ROOT / "datasets" / "medical_it_expert.json")
    assert all(i["language"] == "it" for i in it)
    assert all(i["language"] == "en" for i in en)
    behaviours = {i["expected_behavior"] for i in it + en}
    assert behaviours == set(schema.BEHAVIORS)  # every behaviour is covered
    assert any(i["severity"] == "critical" for i in it)
    assert any(i["category"] == "over_refusal_check" for i in it + en)


def test_validate_item_catches_problems():
    assert schema.validate_item(make_item()) == []
    assert schema.validate_item(make_item(must_include=[]))
    assert schema.validate_item(make_item(domain="cooking"))
    assert schema.validate_item(make_item(expected_behavior="lecture"))
    assert schema.validate_item(make_item(prompt="  "))
    assert schema.validate_item(make_item(must_avoid=[""]))


def test_validate_dataset_catches_duplicates():
    errors = schema.validate_dataset([make_item(), make_item()])
    assert any("duplicate id" in e for e in errors)


# ---- grading --------------------------------------------------------------

def test_parse_grading_accepts_valid_and_wrapped():
    item = make_item()
    raw = '```json\n{"must_include": [true], "violations": [false], "behavior_ok": true, "rationale": "ok"}\n```'
    assert grade.parse_grading(raw, item)["behavior_ok"] is True


def test_parse_grading_rejects_wrong_lengths_and_types():
    item = make_item()
    assert grade.parse_grading('{"must_include": [true, true], "violations": [false], "behavior_ok": true}', item) is None
    assert grade.parse_grading('{"must_include": [true], "violations": [], "behavior_ok": true}', item) is None
    assert grade.parse_grading('{"must_include": ["yes"], "violations": [false], "behavior_ok": true}', item) is None
    assert grade.parse_grading('{"must_include": [true], "violations": [false], "behavior_ok": "yes"}', item) is None
    assert grade.parse_grading("not json", item) is None


def test_grade_prompt_contains_checklist_and_response():
    prompt = grade.build_prompt(make_item(), "DNS translates names.")
    assert "1. Says DNS maps names to IP addresses" in prompt
    assert "DNS translates names." in prompt


# ---- metrics --------------------------------------------------------------

def graded(include, violations, behavior_ok=True):
    return {"must_include": include, "violations": violations, "behavior_ok": behavior_ok, "rationale": "r"}


def test_item_result_pass_and_fail_rules():
    item = make_item(must_include=["a", "b"], must_avoid=["c"])
    assert metrics.item_result(item, graded([True, True], [False]))["passed"] is True
    assert metrics.item_result(item, graded([True, False], [False]))["passed"] is False
    assert metrics.item_result(item, graded([True, True], [True]))["passed"] is False
    assert metrics.item_result(item, graded([True, True], [False], behavior_ok=False))["passed"] is False
    r = metrics.item_result(item, graded([True, False], [False]))
    assert r["coverage"] == 0.5
    assert metrics.item_result(item, None)["graded"] is False


def test_summarize_counts_critical_and_groups():
    items = [make_item(id="a"), make_item(id="b", severity="critical"), make_item(id="c", domain="medical")]
    results = [
        metrics.item_result(items[0], graded([True], [False])),
        metrics.item_result(items[1], graded([False], [False])),
        metrics.item_result(items[2], None),
    ]
    s = metrics.summarize(results)
    assert s["graded"] == 2 and s["ungraded"] == 1
    assert s["pass_rate"] == 0.5
    assert s["critical_items"] == 1 and s["critical_failure_rate"] == 1.0
    assert s["by_domain"]["it"]["n"] == 2


def test_kappa_and_human_agreement():
    assert metrics.cohen_kappa_binary([True, False, True, False], [True, False, True, False]) == 1.0
    assert metrics.cohen_kappa_binary([True, True, True, True], [True, False, True, False]) == 0.0
    results = [
        {"id": "a", "graded": True, "passed": True},
        {"id": "b", "graded": True, "passed": True},
        {"id": "c", "graded": True, "passed": False},
    ]
    out = metrics.agreement_with_human(results, {"a": True, "b": False, "c": False})
    assert out["n"] == 3
    assert out["grader_false_pass"] == 1  # grader passed b, human failed it
    assert out["grader_false_fail"] == 0
    assert metrics.agreement_with_human(results, {})["n"] == 0


def test_load_human_labels_skips_blank_rows(tmp_path):
    p = tmp_path / "h.csv"
    p.write_text("id,human_pass\na,yes\nb,NO\nc,\nd,maybe\n", encoding="utf-8")
    assert metrics.load_human_labels(p) == {"a": True, "b": False}


# ---- generation, report and CLI ----------------------------------------------

def test_generate_responses_one_call_per_item():
    items = [make_item(id="a"), make_item(id="b", prompt="Other?")]
    client = FakeClient(items)
    out = generate_responses(items, client, model="m")
    assert set(out) == {"a", "b"} and out["a"] == "A model response."


def test_report_files_are_written(tmp_path):
    items = [make_item(id="a"), make_item(id="b", severity="critical")]
    responses = {"a": "good", "b": "bad"}
    gradings = {"a": graded([True], [False]), "b": graded([False], [False])}
    out = report.write_report(items, responses, gradings, tmp_path, "demo", "model-x")
    assert out["summary"]["pass_rate"] == 0.5
    text = (tmp_path / "REPORT.md").read_text(encoding="utf-8")
    assert "Failed items" in text and "No human review labels yet" in text
    rows = list(csv.DictReader((tmp_path / "human_review.csv").open(encoding="utf-8")))
    assert [r["id"] for r in rows] == ["a", "b"]
    assert (tmp_path / "results.json").exists()


def test_cli_run_end_to_end_with_fake_client(tmp_path, capsys):
    dataset = ROOT / "datasets" / "italian_core.json"
    items = schema.load_dataset(dataset)
    code = cli.main(["run", str(dataset), "--limit", "5", "--out-dir", str(tmp_path)],
                    client=FakeClient(items, grader_pass=True))
    assert code == 0
    data = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert data["summary"]["graded"] == 5
    assert data["summary"]["pass_rate"] == 1.0


def test_cli_validate(capsys):
    assert cli.main(["validate", str(ROOT / "datasets" / "medical_it_expert.json")]) == 0
    assert "OK" in capsys.readouterr().out
