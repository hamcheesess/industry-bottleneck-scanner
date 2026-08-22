import json
from datetime import date

from industry_bottleneck_scanner.eod_market_data import CollectionDiagnostics
from industry_bottleneck_scanner.market_trigger import IndustryMarketTrigger, MarketTriggerPolicy
from industry_bottleneck_scanner.market_trigger_artifacts import write_market_trigger_artifact


def test_trigger_artifact_has_as_of_provenance_policy_and_coverage(tmp_path) -> None:
    trigger = IndustryMarketTrigger(
        bucket="Electrical Equipment",
        company_count=4,
        market_outperform_breadth=0.75,
        sector_outperform_breadth=0.5,
        near_high_breadth=0.5,
        abnormal_volume_breadth=0.25,
        median_market_relative_3m=0.1,
        median_sector_relative_3m=0.05,
        score=65.0,
        triggered=True,
        reasons=(),
    )
    path = tmp_path / "trigger.json"
    write_market_trigger_artifact(
        path,
        as_of=date(2026, 8, 21),
        benchmark_ticker="IWB",
        source="massive_grouped_daily_adjusted",
        triggers=(trigger,),
        policy=MarketTriggerPolicy(),
        diagnostics=CollectionDiagnostics(4, 4, (), (), 280, 1, 279),
    )

    payload = json.loads(path.read_text())
    assert payload["schema_version"] == "industry-market-trigger-v1"
    assert payload["as_of"] == "2026-08-21"
    assert payload["aggregation"] == "company_membership_bottom_up"
    assert payload["coverage"]["cache_dates"] == 279
    assert payload["triggers"][0]["bucket"] == "Electrical Equipment"
