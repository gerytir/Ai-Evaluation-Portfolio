"""Judge-quality metrics. Pure functions, testable without network."""
from __future__ import annotations

LABELS = ("A", "B", "tie")


def agreement(gold: list[str], pred: list[str]) -> float | None:
    """Share of pairs where the prediction equals the gold label."""
    if not gold:
        return None
    return round(sum(g == p for g, p in zip(gold, pred)) / len(gold), 3)


def cohen_kappa(gold: list[str], pred: list[str], labels=LABELS) -> float | None:
    """Cohen's kappa: agreement corrected for the agreement expected by chance."""
    n = len(gold)
    if n == 0:
        return None
    observed = sum(g == p for g, p in zip(gold, pred)) / n
    expected = sum((gold.count(lbl) / n) * (pred.count(lbl) / n) for lbl in labels)
    if expected == 1:
        return 1.0 if observed == 1 else 0.0
    return round((observed - expected) / (1 - expected), 3)


def swap_consistency(rows: list[dict]) -> float | None:
    """Share of pairs where both orders give the same preference."""
    usable = [r for r in rows if r["original"] and r["swapped"]]
    if not usable:
        return None
    same = sum(r["original"]["preference"] == r["swapped"]["preference"] for r in usable)
    return round(same / len(usable), 3)


def first_slot_bias(rows: list[dict]) -> float | None:
    """Among decisive judgments, share that picked the response shown first.

    In the original order that is A. In the swapped order the first slot holds
    the original B, so a mapped preference of 'B' means the first slot won.
    0.5 means no bias; values far from 0.5 mean the judge favours a position.
    """
    first_wins = decisive = 0
    for r in rows:
        if r["original"] and r["original"]["preference"] != "tie":
            decisive += 1
            first_wins += r["original"]["preference"] == "A"
        if r["swapped"] and r["swapped"]["preference"] != "tie":
            decisive += 1
            first_wins += r["swapped"]["preference"] == "B"
    return round(first_wins / decisive, 3) if decisive else None


def mean_score_gap(rows: list[dict], gold: dict[str, str]) -> float | None:
    """Average (winner total - loser total) on the rubric, for pairs with a gold winner."""
    gaps = []
    for r in rows:
        g = gold.get(r["id"])
        if g in ("A", "B") and r["original"]:
            s = r["original"]["scores"]
            tot = {side: sum(s[side].values()) for side in ("A", "B")}
            loser = "B" if g == "A" else "A"
            gaps.append(tot[g] - tot[loser])
    return round(sum(gaps) / len(gaps), 2) if gaps else None


def summarize(rows: list[dict], gold: dict[str, str]) -> dict:
    """rows: output of judge_pair. gold: {pair_id: 'A'|'B'|'tie'}."""
    judged = [r for r in rows if r["final"] is not None]
    ids = [r["id"] for r in judged]
    g = [gold[i] for i in ids]
    orig = [r["original"]["preference"] for r in judged]
    final = [r["final"] for r in judged]
    return {
        "pairs": len(rows),
        "judged": len(judged),
        "agreement_original_order": agreement(g, orig),
        "agreement_final_verdict": agreement(g, final),
        "kappa_final_verdict": cohen_kappa(g, final),
        "swap_consistency": swap_consistency(rows),
        "first_slot_bias": first_slot_bias(rows),
        "mean_score_gap_for_gold_winner": mean_score_gap(rows, gold),
    }
