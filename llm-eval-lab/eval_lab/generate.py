"""Collect responses from the model under test."""
from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_MODEL = os.getenv("TARGET_MODEL", os.getenv("MODEL", "claude-sonnet-5-5"))


def generate_responses(items: list[dict], client, model: str = DEFAULT_MODEL,
                       max_tokens: int = 1000, system: str | None = None) -> dict[str, str]:
    """Ask the target model each prompt, one independent conversation per item."""
    responses: dict[str, str] = {}
    for item in items:
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": item["prompt"]}],
        }
        if system:
            kwargs["system"] = system
        reply = client.messages.create(**kwargs)
        responses[item["id"]] = "".join(
            b.text for b in reply.content if getattr(b, "type", None) == "text"
        ).strip()
    return responses


def save_responses(responses: dict[str, str], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(responses, ensure_ascii=False, indent=2), encoding="utf-8")


def load_responses(path: str | Path) -> dict[str, str]:
    """Load {id: response}. Also usable for responses collected from any other model by hand."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("responses file must be a JSON object {id: response}")
    return {str(k): str(v) for k, v in data.items()}
