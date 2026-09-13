from datetime import datetime, timezone

from industry_bottleneck_scanner.batch_orchestration import (
    compare_cached_batches,
    scan_cached_batch,
)
from industry_bottleneck_scanner.company_metadata import CompanyPeriodMetadata
from industry_bottleneck_scanner.models import Classification
from industry_bottleneck_scanner.transcript_store import FileTranscriptStore
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


def _record(ticker: str, company_id: str, quarter: str, month: int) -> CompanyPeriodMetadata:
    return CompanyPeriodMetadata(
        ticker=ticker,
        company_id=company_id,
        quarter=quarter,
        published_at=datetime(2026, month, 6, 20, 0, tzinfo=timezone.utc),
        classification=Classification(industry="Electrical Equipment"),
    )


def _save(store: FileTranscriptStore, ticker: str, quarter: str, text: str) -> None:
    store.save(
        EarningsCallTranscript(
            provider="fixture",
            ticker=ticker,
            fiscal_quarter=quarter,
            turns=(TranscriptTurn(speaker="CEO", title="CEO", text=text),),
        )
    )


def test_cached_batch_never_needs_provider_and_reports_missing_cache(tmp_path) -> None:
    store = FileTranscriptStore(tmp_path / "transcripts")
    _save(
        store,
        "POWL",
        "2026Q2",
        "Backlog reached a record level and capacity remains constrained.",
    )
    records = (
        _record("POWL", "issuer-powl", "2026Q2", 5),
        _record("NVT", "issuer-nvt", "2026Q2", 5),
    )

    result = scan_cached_batch(records, provider="fixture", transcript_store=store)

    assert [item.status for item in result.companies] == ["scanned", "missing_cache"]
    assert result.missing_transcripts == 1
    assert any(signal.metric == "backlog_strength" for signal in result.signals)


def test_multi_company_cached_windows_feed_acceleration(tmp_path) -> None:
    store = FileTranscriptStore(tmp_path / "transcripts")
    current = (
        _record("AAA", "issuer-a", "2026Q2", 5),
        _record("BBB", "issuer-b", "2026Q2", 5),
        _record("CCC", "issuer-c", "2026Q2", 5),
    )
    baseline = (_record("AAA", "issuer-a", "2026Q1", 2),)

    for record in current:
        _save(
            store,
            record.ticker,
            record.quarter,
            "Backlog reached a record level and capacity remains constrained.",
        )
    _save(
        store,
        "AAA",
        "2026Q1",
        "Backlog reached a record level and capacity remains constrained.",
    )

    current_result = scan_cached_batch(current, provider="fixture", transcript_store=store)
    baseline_result = scan_cached_batch(baseline, provider="fixture", transcript_store=store)
    acceleration = compare_cached_batches(current_result, baseline_result)

    electrical = next(item for item in acceleration if item.bucket == "Electrical Equipment")
    assert electrical.breadth_current == 3
    assert electrical.breadth_baseline == 1
    assert electrical.core_pair_present is True
    assert electrical.triggered is True
    assert electrical.confirmed is False


def test_batch_respects_company_bound(tmp_path) -> None:
    store = FileTranscriptStore(tmp_path / "transcripts")
    records = tuple(_record(ticker, f"issuer-{ticker}", "2026Q2", 5) for ticker in ("AAA", "BBB"))
    for record in records:
        _save(store, record.ticker, record.quarter, "Pricing remains strong.")

    result = scan_cached_batch(
        records,
        provider="fixture",
        transcript_store=store,
        max_companies=1,
    )

    assert len(result.companies) == 1
    assert result.companies[0].ticker == "AAA"
