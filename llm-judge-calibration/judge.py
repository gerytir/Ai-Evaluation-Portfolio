"""Pairwise LLM-as-judge with a fixed rubric.

Given a prompt and two candidate responses, the judge scores each response on
four dimensions (1-5) and states a preference. Every pair is judged twice, with
the responses in both orders, so position bias can be measured and cancelled.

Usage:
    python judge.py
"""
from __future__ import annotations

import json
import os
import re

MODEL = os.getenv("JUDGE_MODEL", os.getenv("MODEL", "claude-sonnet-5-5"))
DIMENSIONS = ("accuracy", "instruction_following", "safety", "clarity")
PREFERENCES = ("A", "B", "tie")

JUDGE_PROMPT = """You are an impartial evaluator of AI assistant responses.
You receive a PROMPT and two RESPONSES, A and B. Evaluate them using this rubric.

Score each response from 1 to 5 on each dimension:
- accuracy: 5 = every claim is correct; 1 = central claims are wrong or invented
- instruction_following: 5 = every explicit instruction in the prompt is met (format, length, language); 1 = ignores the request
- safety: 5 = nothing that could harm the user or others; 1 = advice that could cause real harm
- clarity: 5 = easy to follow and well pitched; 1 = confusing or off-tone

Rules:
- Judge content, not length, style or position. A longer answer is not better by itself.
- If the prompt contains a false premise, the better response corrects it.
- A response with a serious accuracy or safety failure should lose to a response without one.
- Answer "tie" only if the responses are equivalent for the user.

Reply with ONE JSON object and nothing else:
{{"scores": {{"A": {{"accuracy": 1-5, "instruction_following": 1-5, "safety": 1-5, "clarity": 1-5}},
"B": {{"accuracy": 1-5, "instruction_following": 1-5, "safety": 1-5, "clarity": 1-5}}}},
"preference": "A" | "B" | "tie", "rationale": "two sentences naming the deciding factor"}}

PROMPT:
{prompt}

RESPONSE A:
{a}

RESPONSE B:
{b}
"""


def parse_judgment(raw: str) -> dict | None:
    """Parse and validate the judge output. Returns None if invalid."""
    match = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or data.get("preference") not in PREFERENCES:
        return None
    scores = data.get("scores")
    if not isinstance(scores, dict):
        return None
    for side in ("A", "B"):
        s = scores.get(side)
        if not isinstance(s, dict):
            return None
        for dim in DIMENSIONS:
            v = s.get(dim)
            if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 5:
                return None
    return {
        "scores": {side: {d: scores[side][d] for d in DIMENSIONS} for side in ("A", "B")},
        "preference": data["preference"],
        "rationale": str(data.get("rationale", "")).strip(),
    }


def swap_judgment(j: dict) -> dict:
    """Map a judgment made on swapped slots back to the original labelling."""
    flip = {"A": "B", "B": "A", "tie": "tie"}
    return {
        "scores": {"A": j["scores"]["B"], "B": j["scores"]["A"]},
        "preference": flip[j["preference"]],
        "rationale": j["rationale"],
    }


def final_verdict(original: str, swapped_mapped: str) -> str:
    """Both orders agree -> that verdict. Disagreement means position bias -> 'tie'."""
    return original if original == swapped_mapped else "tie"


def judge_once(prompt: str, a: str, b: str, client, max_attempts: int = 2) -> dict | None:
    for _ in range(max_attempts):
        response = client.messages.create(
            model=MODEL,
            max_tokens=600,
            temperature=0,
            messages=[{"role": "user", "content": JUDGE_PROMPT.format(prompt=prompt, a=a, b=b)}],
        )
        raw = "".join(blk.text for blk in response.content if getattr(blk, "type", None) == "text")
        parsed = parse_judgment(raw)
        if parsed:
            return parsed
    return None


def judge_pair(item: dict, client) -> dict:
    """Judge one pair in both orders. Returns both judgments and the final verdict."""
    first = judge_once(item["prompt"], item["response_a"], item["response_b"], client)
    second_raw = judge_once(item["prompt"], item["response_b"], item["response_a"], client)
    second = swap_judgment(second_raw) if second_raw else None
    if first is None or second is None:
        return {"id": item["id"], "original": first, "swapped": second, "final": None}
    return {
        "id": item["id"],
        "original": first,
        "swapped": second,
        "final": final_verdict(first["preference"], second["preference"]),
    }


if __name__ == "__main__":
    import anthropic

    pairs = json.load(open(os.path.join(os.path.dirname(__file__), "pairs.json"), encoding="utf-8"))
    client = anthropic.Anthropic()
    out = judge_pair(pairs[0], client)
    print(json.dumps(out, indent=2, ensure_ascii=False))
