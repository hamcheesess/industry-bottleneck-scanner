from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .aggregation import AccelerationSnapshot
from .market_trigger import IndustryMarketTrigger

CausalDiagnosisClass = Literal[
    "structural_operating",
    "narrative_led",
    "mixed_or_early",
    "unresolved",
]


@dataclass(frozen=True)
class OperatingCoverage:
    expected_companies: int
    paired_companies_with_documents: int

    def __post_init__(self) -> None:
        if self.expected_companies < 0:
            raise ValueError("expected_companies must be non-negative")
        if self.paired_companies_with_documents < 0:
            raise ValueError("paired_companies_with_documents must be non-negative")
        if self.paired_companies_with_documents > self.expected_companies:
            raise ValueError("paired_companies_with_documents cannot exceed expected_companies")

    @property
    def paired_coverage_ratio(self) -> float:
        if self.expected_companies == 0:
            return 0.0
        return self.paired_companies_with_documents / self.expected_companies


@dataclass(frozen=True)
class CausalDiagnosisPolicy:
    min_paired_coverage_ratio: float = 0.50

    def __post_init__(self) -> None:
        if not 0 <= self.min_paired_coverage_ratio <= 1:
            raise ValueError("min_paired_coverage_ratio must be between 0 and 1")


@dataclass(frozen=True)
class CausalDiagnosis:
    bucket: str
    classification: CausalDiagnosisClass
    market_triggered: bool
    operating_stage: str
    paired_coverage_ratio: float
    reasons: tuple[str, ...]


def diagnose_market_trigger(
    market: IndustryMarketTrigger,
    *,
    operating: AccelerationSnapshot | None,
    coverage: OperatingCoverage,
    policy: CausalDiagnosisPolicy = CausalDiagnosisPolicy(),
) -> CausalDiagnosis:
    """Classify a market move without confusing missing documents with narrative-only evidence.

    `narrative_led` is only available when document coverage is sufficient. Missing or stale
    operating sources therefore fail closed as `unresolved` instead of being interpreted as
    evidence that the market move lacks a structural cause.
    """

    reasons: list[str] = []
    ratio = coverage.paired_coverage_ratio

    if not market.triggered:
        reasons.append("market_not_triggered")
        classification: CausalDiagnosisClass = "unresolved"
        operating_stage = "not_evaluated"
    elif ratio < policy.min_paired_coverage_ratio:
        reasons.append("insufficient_operating_coverage")
        classification = "unresolved"
        operating_stage = "coverage_blocked"
    elif operating is None:
        reasons.append("no_operating_acceleration_detected")
        classification = "narrative_led"
        operating_stage = "none"
    elif operating.confirmed:
        reasons.append("operating_acceleration_confirmed")
        classification = "structural_operating"
        operating_stage = "confirmed"
    elif operating.triggered:
        reasons.append("operating_acceleration_triggered")
        classification = "structural_operating"
        operating_stage = "triggered"
    elif operating.watchlisted or operating.change_reasons:
        reasons.append("partial_operating_support")
        classification = "mixed_or_early"
        operating_stage = "watchlisted" if operating.watchlisted else "weak_change"
    else:
        reasons.append("sufficient_coverage_without_operating_support")
        classification = "narrative_led"
        operating_stage = "observing"

    return CausalDiagnosis(
        bucket=market.bucket,
        classification=classification,
        market_triggered=market.triggered,
        operating_stage=operating_stage,
        paired_coverage_ratio=round(ratio, 4),
        reasons=tuple(reasons),
    )
