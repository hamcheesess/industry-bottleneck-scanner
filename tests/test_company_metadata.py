import pytest

from industry_bottleneck_scanner.company_metadata import load_company_period_metadata_csv


def test_metadata_requires_explicit_timezone_aware_publication_time() -> None:
    text = """ticker,company_id,quarter,published_at,sector,industry,subindustry,published_at_source_url
POWL,issuer-powl,2026Q2,2026-05-06T20:00:00+00:00,Industrials,Electrical Equipment,Power Equipment,https://example.test/event
"""
    records = load_company_period_metadata_csv(text)

    assert len(records) == 1
    assert records[0].ticker == "POWL"
    assert records[0].published_at.utcoffset() is not None
    assert records[0].classification.subindustry == "Power Equipment"
    assert records[0].published_at_source_url == "https://example.test/event"


def test_metadata_rejects_naive_datetime() -> None:
    text = """ticker,company_id,quarter,published_at
POWL,issuer-powl,2026Q2,2026-05-06T20:00:00
"""
    with pytest.raises(ValueError, match="timezone"):
        load_company_period_metadata_csv(text)


def test_metadata_rejects_duplicate_ticker_quarter() -> None:
    text = """ticker,company_id,quarter,published_at
POWL,issuer-powl,2026Q2,2026-05-06T20:00:00+00:00
POWL,issuer-powl,2026Q2,2026-05-06T20:00:00+00:00
"""
    with pytest.raises(ValueError, match="duplicate"):
        load_company_period_metadata_csv(text)
