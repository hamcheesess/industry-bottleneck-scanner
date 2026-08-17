from dataclasses import dataclass
from typing import cast

from industry_bottleneck_scanner.aggregation import AccelerationSnapshot
from industry_bottleneck_scanner.causal_diagnosis import (
    OperatingCoverage,
    diagnose_market_trigger,
)
from industry_bottleneck_scanner.market_trigger import IndustryMarketTrigger


@dataclass
class FakeOperating:
    confirmed: bool = False
    triggered: bool = False
    watchlisted: bool = False
    change_reasons: tuple[str, ...] = ()


def market(*, triggered: bool = True) -> IndustryMarketTrigger:
    return IndustryMarketTrigger(
        bucket="AI Infrastructure",
        company_count=8,
        market_outperform_breadth=0.75,
        sector_outperform_breadth=0.625,
        near_high_breadth=0.5,
        abnormal_volume_breadth=0.5,
        median_market_relative_3m=0.12,
        median_sector_relative_3m=0.08,
        score=70.0,
        triggered=triggered,
        reasons=(),
    )


def operating(**kwargs) -> AccelerationSnapshot:
    return cast(AccelerationSnapshot, FakeOperating(**kwargs))


def test_missing_operating_documents_fail_closed_instead_of_becoming_narrative_led() -> None:
    result = diagnose_market_trigger(
        market(),
        operating=None,
        coverage=OperatingCoverage(expected_companies=8, paired_companies_with_documents=2),
    )
    assert result.classification == "unresolved"
    assert "insufficient_operating_coverage" in result.reasons


def test_sufficient_coverage_without_acceleration_is_narrative_led() -> None:
    result = diagnose_market_trigger(
        market(),
        operating=None,
        coverage=OperatingCoverage(expected_companies=8, paired_companies_with_documents=6),
    )
    assert result.classification == "narrative_led"


def test_confirmed_operating_acceleration_is_structural() -> None:
    result = diagnose_market_trigger(
        market(),
        operating=operating(confirmed=True, triggered=True),
        coverage=OperatingCoverage(expected_companies=8, paired_companies_with_documents=6),
    )
    assert result.classification == "structural_operating"
    assert result.operating_stage == "confirmed"


def test_partial_operating_change_is_mixed_or_early() -> None:
    result = diagnose_market_trigger(
        market(),
        operating=operating(watchlisted=True, change_reasons=("breadth_gain",)),
        coverage=OperatingCoverage(expected_companies=8, paired_companies_with_documents=6),
    )
    assert result.classification == "mixed_or_early"


def test_non_triggered_market_bucket_is_not_causally_promoted() -> None:
    result = diagnose_market_trigger(
        market(triggered=False),
        operating=operating(confirmed=True, triggered=True),
        coverage=OperatingCoverage(expected_companies=8, paired_companies_with_documents=8),
    )
    assert result.classification == "unresolved"
    assert "market_not_triggered" in result.reasons
