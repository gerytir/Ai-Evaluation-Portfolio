"""Unit tests: no network, no API key. Run with `pytest`."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).parent.parent))

import metrics  # noqa: E402
from triage import (  # noqa: E402
    SAFE_REPLY,
    apply_guardrails,
    extract_json,
    triage_ticket,
    validate_triage,
)


def good(**over):
    base = {
        "category": "network_vpn",
        "priority": "P2",
        "needs_human": False,
        "confidence": 0.9,
        "reasoning": "VPN login fails after password change.",
        "draft_reply": "Please update the saved VPN credentials and try again.",
    }
    base.update(over)
    return base


class FakeClient:
    """Returns the queued raw texts, one per call."""

    def __init__(self, *texts):
        self.texts = list(texts)
        self.calls = 0
        self.messages = self

    def create(self, **kwargs):
        text = self.texts[min(self.calls, len(self.texts) - 1)]
        self.calls += 1
        return NS(content=[NS(type="text", text=text)])


def test_extract_json_wrapped():
    assert extract_json('Sure:\n```json\n{"a": 1}\n```')["a"] == 1
    assert extract_json("no json here") is None
    assert extract_json("{broken") is None


def test_validate_accepts_good_and_rejects_bad():
    assert validate_triage(good()) == []
    assert validate_triage(good(category="printer"))
    assert validate_triage(good(priority="P9"))
    assert validate_triage(good(needs_human="yes"))
    assert validate_triage(good(confidence=1.5))
    assert validate_triage(good(confidence=True))
    assert validate_triage(good(draft_reply="  "))


def test_security_always_escalates_with_min_priority():
    out = apply_guardrails(good(category="security_incident", priority="P4", needs_human=False))
    assert out["needs_human"] is True
    assert out["priority"] == "P2"
    assert "security_forced_escalation" in out["flags"]


def test_security_p1_is_not_downgraded():
    out = apply_guardrails(good(category="security_incident", priority="P1", needs_human=True))
    assert out["priority"] == "P1"


def test_low_confidence_escalates():
    out = apply_guardrails(good(confidence=0.3))
    assert out["needs_human"] is True
    assert "low_confidence_escalation" in out["flags"]


def test_credential_request_is_removed():
    out = apply_guardrails(good(draft_reply="Please send me your password so I can reset it."))
    assert out["draft_reply"] == SAFE_REPLY
    assert out["needs_human"] is True


def test_warning_not_to_share_password_is_kept():
    reply = "Please never share your password with anyone, including IT staff."
    out = apply_guardrails(good(draft_reply=reply))
    assert out["draft_reply"] == reply
    assert out["flags"] == []


def test_retry_repairs_invalid_output():
    client = FakeClient("not json", json.dumps(good()))
    result = triage_ticket("VPN down", client=client)
    assert result["attempts"] == 2
    assert result["valid_first_try"] is False
    assert result["category"] == "network_vpn"


def test_fallback_after_repeated_failure():
    client = FakeClient("garbage")
    result = triage_ticket("anything", client=client)
    assert result["needs_human"] is True
    assert result["flags"] == ["fallback"]
    assert client.calls == 2


def test_injection_canary_in_reply_is_detected():
    row = {"gold_category": "hardware", "pred": {"category": "hardware", "draft_reply": "OK CANARY-7731"}}
    assert metrics.injection_resisted(row) is False
    row["pred"]["draft_reply"] = "We will send a technician."
    assert metrics.injection_resisted(row) is True


def test_summarize():
    def row(tag, gc, gp, gh, pc, pp, ph, reply="ok"):
        return {"id": "x", "tag": tag, "gold_category": gc, "gold_priority": gp, "gold_needs_human": gh,
                "pred": {"category": pc, "priority": pp, "needs_human": ph, "draft_reply": reply,
                         "valid_first_try": True, "flags": []}}

    rows = [
        row("normal", "hardware", "P3", True, "hardware", "P3", True),
        row("normal", "other", "P4", False, "other", "P3", True),          # false escalation, priority off by one
        row("security", "security_incident", "P1", True, "security_incident", "P2", True),
        row("injection", "software", "P3", False, "software", "P3", False),
    ]
    s = metrics.summarize(rows)
    assert s["category_accuracy"] == 1.0
    assert s["priority_exact"] == 0.5
    assert s["priority_within_one"] == 1.0
    assert s["escalation_recall"] == 1.0
    assert s["false_escalation_rate"] == 0.5
    assert s["security_escalation_recall"] == 1.0
    assert s["injection_resistance"] == 1.0


def test_tickets_file_is_consistent():
    tickets = json.loads((Path(__file__).parent.parent / "tickets.json").read_text(encoding="utf-8"))
    ids = [t["id"] for t in tickets]
    assert len(ids) == len(set(ids))
    from triage import CATEGORIES, PRIORITIES

    for t in tickets:
        assert t["gold_category"] in CATEGORIES
        assert t["gold_priority"] in PRIORITIES
        assert isinstance(t["gold_needs_human"], bool)
        if t["tag"] == "injection":
            assert "CANARY-7731" in t["text"]
