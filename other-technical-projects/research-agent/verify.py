"""Claim-by-claim check: does the text cited by the source actually support the claim?

The judge sees ONLY the claim and the passages cited by the web search, never
its own memory: if the passage is not enough, the verdict is "unsupported".
"""
from __future__ import annotations

import json
import os
import re

JUDGE_MODEL = os.getenv("JUDGE_MODEL", os.getenv("MODEL", "claude-sonnet-5-5"))

JUDGE_PROMPT = """You are a strict evaluator. You receive a CLAIM and the PASSAGES that the source
cites in its support. Decide whether the passages support the claim.

Allowed verdicts:
- "supported": everything the claim says is present in the passages.
- "partial": part of the claim is supported, part is not (added detail, different number, generalization).
- "unsupported": the passages do not support the claim or contradict it.

Use only the passages provided. Do not use outside knowledge, even if the claim seems true to you.

Reply with a single JSON object: {{"verdict": "...", "reason": "one sentence"}}

CLAIM:
{claim}

PASSAGES:
{passages}
"""

VALID = {"supported", "partial", "unsupported"}


def parse_verdict(raw: str) -> dict:
    """Extract the JSON from the judge's text; an invalid verdict becomes 'unsupported'."""
    match = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            verdict = str(data.get("verdict", "")).strip().lower()
            if verdict in VALID:
                return {"verdict": verdict, "reason": str(data.get("reason", "")).strip()}
        except json.JSONDecodeError:
            pass
    return {"verdict": "unsupported", "reason": "Judge reply could not be parsed"}


def judge_claim(claim_text: str, sources: list[dict], client=None) -> dict:
    if client is None:
        import anthropic

        client = anthropic.Anthropic()
    passages = "\n\n".join(f"- {s['cited_text']}" for s in sources if s.get("cited_text"))
    if not passages:
        return {"verdict": "unsupported", "reason": "No cited passage available"}
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=300,
        temperature=0,
        messages=[
            {"role": "user", "content": JUDGE_PROMPT.format(claim=claim_text, passages=passages)}
        ],
    )
    text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
    return parse_verdict(text)
