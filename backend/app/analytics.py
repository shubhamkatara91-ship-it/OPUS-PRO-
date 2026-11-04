"""Transparent descriptive analytics for verified historical observations."""
from collections import Counter
from math import sqrt
from typing import Iterable


ALLOWED_LABELS = {"BIG", "SMALL"}


def analyze_labels(labels: Iterable[str]) -> dict[str, object]:
    cleaned = [str(label).strip().upper() for label in labels]
    if not cleaned:
        return {
            "sample_size": 0,
            "counts": {"BIG": 0, "SMALL": 0},
            "observed_rates": {"BIG": None, "SMALL": None},
            "baseline": None,
            "note": "No historical observations supplied; no estimate can be calculated.",
        }

    invalid = sorted(set(cleaned) - ALLOWED_LABELS)
    if invalid:
        raise ValueError(f"Unsupported labels: {', '.join(invalid)}")

    counts = Counter(cleaned)
    n = len(cleaned)
    rates = {label: counts[label] / n for label in sorted(ALLOWED_LABELS)}

    # Wilson 95% interval for the observed BIG proportion; descriptive, not predictive.
    p = rates["BIG"]
    z = 1.96
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    margin = z * sqrt((p * (1 - p) / n) + (z * z / (4 * n * n))) / denominator

    return {
        "sample_size": n,
        "counts": {label: counts[label] for label in sorted(ALLOWED_LABELS)},
        "observed_rates": rates,
        "big_rate_wilson_95": {
            "lower": max(0.0, center - margin),
            "upper": min(1.0, center + margin),
        },
        "baseline": "Historical frequency only; not a forecast or guarantee.",
        "note": "Descriptive statistics do not establish the next outcome. Validate source quality and test out-of-sample before any forecasting claim.",
    }
