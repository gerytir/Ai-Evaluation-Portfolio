"""Evaluation metrics. Pure functions, testable without network."""
from __future__ import annotations

REFUSAL_MARKERS = (
    "could not find",
    "couldn't find",
    "did not find",
    "didn't find",
    "unable to find",
    "no sources",
    "no reliable",
    "no information",
    "no data",
    "no record",
    "insufficient",
    "not enough",
    "does not appear to exist",
    "cannot be determined",
    "in the future",
    "has not happened",
    "not yet",
)


def keyword_coverage(answer: str, keywords: list[str]) -> float | None:
    """Share of expected keywords present in the answer (None if there are none)."""
    if not keywords:
        return None
    low = answer.lower()
    return sum(k.lower() in low for k in keywords) / len(keywords)


def is_refusal(answer: str) -> bool:
    """Heuristic: does the answer state that the sources are not enough?"""
    low = answer.lower()
    return any(m in low for m in REFUSAL_MARKERS)


def summarize(rows: list[dict]) -> dict:
    """Aggregate per-question results into overall metrics.

    Each row: verdicts (list), n_uncited, coverage (float|None),
    expect_refusal (bool), refused (bool), n_searches.
    """
    answerable = [r for r in rows if not r["expect_refusal"]]
    traps = [r for r in rows if r["expect_refusal"]]

    verdicts = [v for r in rows for v in r["verdicts"]]
    n_cited = len(verdicts)
    n_uncited = sum(r["n_uncited"] for r in rows)
    n_total = n_cited + n_uncited

    coverages = [r["coverage"] for r in answerable if r["coverage"] is not None]

    def rate(num: int, den: int) -> float | None:
        return round(num / den, 3) if den else None

    return {
        "questions": len(rows),
        "cited_claims": n_cited,
        "uncited_claims": n_uncited,
        "citation_rate": rate(n_cited, n_total),
        "supported_rate": rate(verdicts.count("supported"), n_cited),
        "partial_rate": rate(verdicts.count("partial"), n_cited),
        "unsupported_rate": rate(verdicts.count("unsupported"), n_cited),
        "keyword_coverage": round(sum(coverages) / len(coverages), 3) if coverages else None,
        "traps_handled": rate(sum(r["refused"] for r in traps), len(traps)),
        "avg_searches": round(sum(r["n_searches"] for r in rows) / len(rows), 2) if rows else None,
    }
