"""Distribution drift checks for categorical fields.

Computes Population Stability Index (PSI) and Jensen-Shannon Divergence
(JSD, base 2, bounded [0, 1]) between a reference distribution (e.g.,
gold labels or yesterday's run) and a candidate distribution (e.g.,
today's outputs). Both metrics are robust to unseen categories thanks
to additive smoothing.

PSI severity bands follow the common convention:
  < 0.10   stable
  0.10-0.25 moderate shift
  > 0.25   significant shift

Why two metrics: PSI is the industry standard and easy to communicate
in interviews; JSD is bounded which makes it easier to set alert
thresholds. We report both and flag a breach when either exceeds its
threshold.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

DEFAULT_PSI_THRESHOLD = 0.25
DEFAULT_JSD_THRESHOLD = 0.10
DEFAULT_EPSILON = 1e-6


@dataclass(frozen=True)
class FieldDrift:
    """Per-field drift result."""

    field_name: str
    psi: float
    jsd: float
    severity: str
    reference: dict[str, float]
    candidate: dict[str, float]
    reference_n: int
    candidate_n: int
    breaches: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DriftReport:
    """Top-level drift report across all checked fields."""

    fields: list[FieldDrift]
    psi_threshold: float
    jsd_threshold: float
    ok: bool


def categorical_counts(records: list[dict[str, Any]], field_name: str) -> tuple[dict[str, int], int]:
    """Count categorical values for a field, ignoring None / empty / non-string."""

    counts: dict[str, int] = {}
    total = 0
    for record in records:
        value = record.get(field_name)
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned:
            continue
        counts[cleaned] = counts.get(cleaned, 0) + 1
        total += 1
    return counts, total


def _smooth_and_normalize(
    reference_counts: dict[str, int],
    candidate_counts: dict[str, int],
    epsilon: float,
) -> tuple[dict[str, float], dict[str, float]]:
    """Align supports, apply additive smoothing, renormalize to sum to 1."""

    support = set(reference_counts) | set(candidate_counts)
    if not support:
        return {}, {}

    ref_smoothed = {key: float(reference_counts.get(key, 0)) + epsilon for key in support}
    cand_smoothed = {key: float(candidate_counts.get(key, 0)) + epsilon for key in support}

    ref_total = sum(ref_smoothed.values())
    cand_total = sum(cand_smoothed.values())

    ref_norm = {key: value / ref_total for key, value in ref_smoothed.items()}
    cand_norm = {key: value / cand_total for key, value in cand_smoothed.items()}
    return ref_norm, cand_norm


def psi(reference: dict[str, float], candidate: dict[str, float]) -> float:
    """Population Stability Index across an aligned support."""

    if not reference or not candidate:
        return 0.0
    total = 0.0
    for key, ref_p in reference.items():
        cand_p = candidate.get(key, 0.0)
        if ref_p <= 0 or cand_p <= 0:
            continue
        total += (cand_p - ref_p) * math.log(cand_p / ref_p)
    return total


def jsd(reference: dict[str, float], candidate: dict[str, float]) -> float:
    """Jensen-Shannon divergence in base 2, bounded in [0, 1]."""

    if not reference or not candidate:
        return 0.0

    def kl(p: dict[str, float], q: dict[str, float]) -> float:
        total = 0.0
        for key, p_val in p.items():
            q_val = q.get(key, 0.0)
            if p_val <= 0 or q_val <= 0:
                continue
            total += p_val * math.log2(p_val / q_val)
        return total

    mixture = {key: 0.5 * (reference.get(key, 0.0) + candidate.get(key, 0.0))
               for key in set(reference) | set(candidate)}
    return 0.5 * kl(reference, mixture) + 0.5 * kl(candidate, mixture)


def _severity(psi_value: float) -> str:
    if psi_value < 0.10:
        return "stable"
    if psi_value < 0.25:
        return "moderate"
    return "significant"


def compute_drift(
    reference_records: list[dict[str, Any]],
    candidate_records: list[dict[str, Any]],
    fields: list[str],
    *,
    psi_threshold: float = DEFAULT_PSI_THRESHOLD,
    jsd_threshold: float = DEFAULT_JSD_THRESHOLD,
    epsilon: float = DEFAULT_EPSILON,
) -> DriftReport:
    """Compute drift per-field and assemble a report."""

    field_results: list[FieldDrift] = []
    overall_ok = True

    for field_name in fields:
        ref_counts, ref_n = categorical_counts(reference_records, field_name)
        cand_counts, cand_n = categorical_counts(candidate_records, field_name)

        if ref_n == 0 or cand_n == 0:
            field_results.append(
                FieldDrift(
                    field_name=field_name,
                    psi=0.0,
                    jsd=0.0,
                    severity="no_data",
                    reference={},
                    candidate={},
                    reference_n=ref_n,
                    candidate_n=cand_n,
                    breaches=["no_data"],
                )
            )
            overall_ok = False
            continue

        ref_norm, cand_norm = _smooth_and_normalize(ref_counts, cand_counts, epsilon)
        psi_value = psi(ref_norm, cand_norm)
        jsd_value = jsd(ref_norm, cand_norm)

        breaches: list[str] = []
        if psi_value > psi_threshold:
            breaches.append(f"psi {psi_value:.4f} > {psi_threshold}")
        if jsd_value > jsd_threshold:
            breaches.append(f"jsd {jsd_value:.4f} > {jsd_threshold}")

        if breaches:
            overall_ok = False

        field_results.append(
            FieldDrift(
                field_name=field_name,
                psi=psi_value,
                jsd=jsd_value,
                severity=_severity(psi_value),
                reference=ref_norm,
                candidate=cand_norm,
                reference_n=ref_n,
                candidate_n=cand_n,
                breaches=breaches,
            )
        )

    return DriftReport(
        fields=field_results,
        psi_threshold=psi_threshold,
        jsd_threshold=jsd_threshold,
        ok=overall_ok,
    )
