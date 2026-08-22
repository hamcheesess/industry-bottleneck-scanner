from datetime import date

import pytest

from industry_bottleneck_scanner.market_universe import load_market_universe_csv


def test_market_universe_reuses_identity_contract_and_exposes_classification_gaps() -> None:
    snapshot = load_market_universe_csv(
        """ticker,company_name,exchange,cik,sector,bucket,active
AAA,Alpha Inc,NYSE,123,Industrials,Electrical Equipment,true
BBB,Beta Inc,NASDAQ,456,,,true
CCC,Inactive Inc,NYSE,789,Technology,Hardware,false
""",
        as_of=date(2026, 8, 1),
        source="dated-membership-test",
    )

    assert snapshot.active_member_count == 2
    assert snapshot.classification_coverage_ratio == 0.5
    assert snapshot.unclassified_tickers == ("BBB",)
    assert snapshot.entries[0].security_id is not None
    assert snapshot.entries[0].issuer_id == "cik-0000000123"


def test_market_universe_rejects_duplicate_normalized_ticker() -> None:
    with pytest.raises(ValueError, match="duplicate normalized ticker"):
        load_market_universe_csv(
            """ticker,company_name,sector,bucket
BRK.B,Berkshire,Financials,Insurance
BRK-B,Berkshire B,Financials,Insurance
""",
            as_of=date(2026, 8, 1),
            source="test",
        )
