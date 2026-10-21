"""Dataset schema and validation.

Each item is one test prompt plus a checklist that says what a good response
must contain (must_include) and what it must not do (must_avoid).
"""
from __future__ import annotations

import json
from pathlib import Path

LANGUAGES = ("it", "en")
DOMAINS = ("language", "culture", "safety", "medical", "it")
BEHAVIORS = (
    "answer",                 # answer the question directly
    "correct_false_premise",  # challenge a false premise instead of accepting it
    "admit_unknown",          # say the thing does not exist / cannot be verified, do not invent
    "refuse",                 # decline the harmful part of the request
    "urgent_referral",        # direct the user to emergency care immediately
)
SEVERITIES = ("normal", "critical")  # critical: failure could cause harm or presents invented facts as true
REQUIRED_STRINGS = ("id", "prompt", "category", "source_note")


def _string_list(value, allow_empty: bool) -> bool:
    if not isinstance(value, list):
        return False
    if not allow_empty and not value:
        return False
    return all(isinstance(v, str) and v.strip() for v in value)


def validate_item(item) -> list[str]:
    """Return a list of problems with one item (empty list means valid)."""
    if not isinstance(item, dict):
        return ["item is not an object"]
    errors: list[str] = []
    for key in REQUIRED_STRINGS:
        if not isinstance(item.get(key), str) or not item[key].strip():
            errors.append(f"{key} must be a non-empty string")
    if item.get("language") not in LANGUAGES:
        errors.append(f"language must be one of {list(LANGUAGES)}")
    if item.get("domain") not in DOMAINS:
        errors.append(f"domain must be one of {list(DOMAINS)}")
    if item.get("expected_behavior") not in BEHAVIORS:
        errors.append(f"expected_behavior must be one of {list(BEHAVIORS)}")
    if item.get("severity") not in SEVERITIES:
        errors.append(f"severity must be one of {list(SEVERITIES)}")
    if not _string_list(item.get("must_include"), allow_empty=False):
        errors.append("must_include must be a non-empty list of non-empty strings")
    if not _string_list(item.get("must_avoid"), allow_empty=True):
        errors.append("must_avoid must be a list of non-empty strings")
    return errors


def validate_dataset(items) -> list[str]:
    """Validate a whole dataset. Returns readable error lines."""
    if not isinstance(items, list) or not items:
        return ["dataset must be a non-empty list"]
    errors: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        label = item.get("id", f"#{index}") if isinstance(item, dict) else f"#{index}"
        for problem in validate_item(item):
            errors.append(f"{label}: {problem}")
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            if item["id"] in seen:
                errors.append(f"{label}: duplicate id")
            seen.add(item["id"])
    return errors


def load_dataset(path: str | Path) -> list[dict]:
    items = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_dataset(items)
    if errors:
        raise ValueError("Invalid dataset:\n" + "\n".join(errors))
    return items
