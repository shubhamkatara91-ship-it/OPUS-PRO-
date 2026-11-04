"""OPUS PRO independent historical signal analytics.

This is an original, transparent statistical baseline. It is not Mark Pro code,
does not connect to an unverified gaming provider, and does not promise outcomes.
Input outcomes must be chronological (oldest first).
"""
from collections import Counter, defaultdict
from math import log2
from typing import Iterable

VALID = {"BIG", "SMALL"}


def _clean(outcomes: Iterable[str]) -> list[str]:
    values = [str(x).strip().upper() for x in outcomes]
    if any(x not in VALID for x in values):
        raise ValueError("Every outcome must be BIG or SMALL")
    return values


def analyze(outcomes: Iterable[str], min_samples: int = 20) -> dict:
    values = _clean(outcomes)
    n = len(values)
    counts = Counter(values)
    big_pct = counts["BIG"] * 100 / n if n else 0.0
    small_pct = counts["SMALL"] * 100 / n if n else 0.0

    # Recency-weighted frequency: newest observations carry more weight.
    weighted = {"BIG": 0.0, "SMALL": 0.0}
    total_weight = 0.0
    for index, value in enumerate(values):
        weight = 1.0 + (index / max(1, n - 1))
        weighted[value] += weight
        total_weight += weight
    weighted_pct = {
        key: round(weighted[key] * 100 / total_weight, 2) if total_weight else 0.0
        for key in VALID
    }

    transitions = {key: {"BIG": 0, "SMALL": 0} for key in VALID}
    for previous, current in zip(values, values[1:]):
        transitions[previous][current] += 1
    last = values[-1] if values else None
    row_total = sum(transitions[last].values()) if last else 0
    # Laplace smoothing avoids false 0%/100% rates on small samples.
    next_after_last = {
        key: round((transitions[last][key] + 1) * 100 / (row_total + 2), 2)
        for key in VALID
    } if last else None

    streak_value, streak_length = (last, 0) if last else (None, 0)
    for value in reversed(values):
        if value != streak_value:
            break
        streak_length += 1

    if n:
        p = counts["BIG"] / n
        entropy = 0.0 if p in (0, 1) else -(p * log2(p) + (1-p) * log2(1-p))
    else:
        entropy = 0.0

    # Agreement score is descriptive model agreement, NOT calibrated accuracy.
    freq_lean = max(weighted_pct, key=weighted_pct.get) if n else None
    transition_lean = max(next_after_last, key=next_after_last.get) if next_after_last else None
    agreement = 0
    if freq_lean and transition_lean:
        agreement = 100 if freq_lean == transition_lean else 0

    ready = n >= min_samples
    return {
        "engine": "OPUS Statistical Signal Engine v1",
        "mode": "historical_research_only",
        "sample_size": n,
        "minimum_samples": min_samples,
        "status": "ready_for_research" if ready else "insufficient_history",
        "observed_frequency_pct": {"BIG": round(big_pct, 2), "SMALL": round(small_pct, 2)},
        "recency_weighted_frequency_pct": weighted_pct,
        "last_observed": last,
        "current_streak": {"outcome": streak_value, "length": streak_length},
        "transition_counts_after_last": transitions[last] if last else None,
        "smoothed_transition_pct_after_last": next_after_last,
        "binary_entropy": round(entropy, 4),
        "historical_bias": freq_lean if ready else None,
        "model_agreement_score": agreement if ready else None,
        "score_note": "Agreement score compares two descriptive indicators; it is not a probability or verified prediction accuracy.",
        "limitations": [
            "Historical patterns may not persist or predict the next independent outcome.",
            "No live provider feed is connected.",
            "No proprietary Mark Pro algorithm or server logic is reproduced."
        ]
    }


def walk_forward_backtest(outcomes: Iterable[str], min_train: int = 20) -> dict:
    values = _clean(outcomes)
    if min_train < 2:
        raise ValueError("min_train must be at least 2")
    correct = 0
    evaluated = 0
    predictions = []
    for index in range(min_train, len(values)):
        train = values[:index]
        result = analyze(train, min_samples=min_train)
        # Predict only the majority of the training sample; ties are skipped.
        freq = result["observed_frequency_pct"]
        if freq["BIG"] == freq["SMALL"]:
            continue
        predicted = "BIG" if freq["BIG"] > freq["SMALL"] else "SMALL"
        actual = values[index]
        hit = predicted == actual
        evaluated += 1
        correct += int(hit)
        predictions.append({"index": index, "predicted": predicted, "actual": actual, "correct": hit})
    return {
        "engine": "OPUS Statistical Signal Engine v1",
        "method": "expanding_window_majority_baseline",
        "evaluated": evaluated,
        "correct": correct,
        "accuracy_pct": round(correct * 100 / evaluated, 2) if evaluated else None,
        "predictions": predictions[-100:],
        "warning": "Retrospective sample performance is not a guarantee of future accuracy."
    }
