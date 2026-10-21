"""Unit tests: no network, no API key. Run with `pytest`."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).parent.parent))

import metrics  # noqa: E402
from judge import (  # noqa: E402
    final_verdict,
    judge_pair,
    parse_judgment,
    swap_judgment,
)


def scores(a=(5, 5, 5, 5), b=(2, 5, 5, 4)):
    dims = ("accuracy", "instruction_following", "safety", "clarity")
    return {"A": dict(zip(dims, a)), "B": dict(zip(dims, b))}


def judgment(pref="A", **kw):
    return {"scores": scores(**kw), "preference": pref, "rationale": "r"}


class FakeClient:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = 0
        self.messages = self

    def create(self, **kwargs):
        out = self.outputs[min(self.calls, len(self.outputs) - 1)]
        self.calls += 1
        return NS(content=[NS(type="text", text=out)])


def test_parse_valid_and_wrapped():
    raw = "```json\n" + json.dumps(judgment()) + "\n```"
    assert parse_judgment(raw)["preference"] == "A"


def test_parse_rejects_invalid():
    assert parse_judgment("nope") is None
    bad_pref = judgment()
    bad_pref["preference"] = "C"
    assert parse_judgment(json.dumps(bad_pref)) is None
    bad_score = judgment()
    bad_score["scores"]["A"]["accuracy"] = 9
    assert parse_judgment(json.dumps(bad_score)) is None
    missing = judgment()
    del missing["scores"]["B"]["safety"]
    assert parse_judgment(json.dumps(missing)) is None


def test_swap_maps_back_preference_and_scores():
    j = judgment("A", a=(5, 5, 5, 5), b=(1, 1, 1, 1))
    s = swap_judgment(j)
    assert s["preference"] == "B"
    assert s["scores"]["B"]["accuracy"] == 5
    assert s["scores"]["A"]["accuracy"] == 1
    assert swap_judgment(judgment("tie"))["preference"] == "tie"


def test_final_verdict_disagreement_is_tie():
    assert final_verdict("A", "A") == "A"
    assert final_verdict("A", "B") == "tie"


def test_judge_pair_unbiased_judge_gives_consistent_verdict():
    # Slot A wins in the first call, slot B wins in the second (swapped) call: consistent for original A.
    client = FakeClient(json.dumps(judgment("A")), json.dumps(judgment("B")))
    out = judge_pair({"id": "p", "prompt": "q", "response_a": "x", "response_b": "y"}, client)
    assert out["final"] == "A"


def test_judge_pair_position_biased_judge_becomes_tie():
    # The judge always prefers the first slot.
    client = FakeClient(json.dumps(judgment("A")), json.dumps(judgment("A")))
    out = judge_pair({"id": "p", "prompt": "q", "response_a": "x", "response_b": "y"}, client)
    assert out["final"] == "tie"


def test_judge_pair_handles_invalid_output():
    client = FakeClient("garbage")
    out = judge_pair({"id": "p", "prompt": "q", "response_a": "x", "response_b": "y"}, client)
    assert out["final"] is None


def test_agreement_and_kappa():
    gold = ["A", "A", "B", "tie"]
    assert metrics.agreement(gold, ["A", "A", "B", "tie"]) == 1.0
    assert metrics.agreement(gold, ["A", "B", "B", "tie"]) == 0.75
    assert metrics.cohen_kappa(gold, gold) == 1.0
    # always predicting 'A' on balanced-ish labels gives kappa 0
    assert metrics.cohen_kappa(["A", "B", "A", "B"], ["A", "A", "A", "A"]) == 0.0


def test_swap_consistency_and_bias():
    rows = [
        {"id": "1", "original": judgment("A"), "swapped": swap_judgment(judgment("B"))},  # consistent: A
        {"id": "2", "original": judgment("A"), "swapped": swap_judgment(judgment("A"))},  # biased to first slot
    ]
    assert metrics.swap_consistency(rows) == 0.5
    # decisive calls: r1 orig A(first), r1 swapped raw B -> mapped A; first slot = B in swapped order
    # r1 swapped mapped pref is 'A' (not 'B'), so first slot did not win there
    assert metrics.first_slot_bias(rows) is not None


def test_summarize_end_to_end():
    rows = [
        {"id": "1", "original": judgment("A"), "swapped": swap_judgment(judgment("B")), "final": "A"},
        {"id": "2", "original": judgment("B"), "swapped": swap_judgment(judgment("A")), "final": "B"},
    ]
    s = metrics.summarize(rows, {"1": "A", "2": "B"})
    assert s["agreement_final_verdict"] == 1.0
    assert s["swap_consistency"] == 1.0
    assert s["first_slot_bias"] == 0.5


def test_pairs_file_is_consistent():
    pairs = json.loads((Path(__file__).parent.parent / "pairs.json").read_text(encoding="utf-8"))
    ids = [p["id"] for p in pairs]
    assert len(ids) == len(set(ids))
    for p in pairs:
        assert p["gold"] in ("A", "B", "tie")
        assert p["response_a"].strip() and p["response_b"].strip()
