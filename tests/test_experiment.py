from datetime import datetime, timezone

from industry_bottleneck_scanner.company_metadata import CompanyPeriodMetadata
from industry_bottleneck_scanner.experiment import run_comparable_cached_experiment
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


def test_experiment_uses_only_issuers_present_and_cached_in_both_windows(tmp_path) -> None:
    store = FileTranscriptStore(tmp_path / "transcripts")
    current = (
        _record("AAA", "issuer-a", "2026Q2", 5),
        _record("BBB", "issuer-b", "2026Q2", 5),
        _record("CCC", "issuer-c", "2026Q2", 5),
    )
    baseline = (
        _record("AAA", "issuer-a", "2026Q1", 2),
        _record("BBB", "issuer-b", "2026Q1", 2),
        _record("DDD", "issuer-d", "2026Q1", 2),
    )

    for ticker in ("AAA", "BBB", "CCC"):
        _save(
            store,
            ticker,
            "2026Q2",
            "Backlog reached a record level and capacity remains constrained.",
        )
    _save(
        store,
        "AAA",
        "2026Q1",
        "Backlog reached a record level and capacity remains constrained.",
    )
    # BBB baseline is intentionally absent. A raw comparison would make current breadth
    # look larger simply because current transcript coverage is more complete.

    result = run_comparable_cached_experiment(
        current,
        baseline,
        provider="fixture",
        transcript_store=store,
    )

    assert result.diagnostics.metadata_matched == 2
    assert result.diagnostics.eligible_companies == 1
    assert result.diagnostics.current_only_company_ids == ("issuer-c",)
    assert result.diagnostics.baseline_only_company_ids == ("issuer-d",)
    assert result.diagnostics.baseline_missing_cache_ids == ("issuer-b",)
    assert {signal.company_id for signal in result.current.signals} == {"issuer-a"}
    assert {signal.company_id for signal in result.baseline.signals} == {"issuer-a"}

    electrical = next(item for item in result.acceleration if item.bucket == "Electrical Equipment")
    assert electrical.breadth_current == 1
    assert electrical.breadth_baseline == 1
    assert electrical.breadth_change == 0
    assert electrical.triggered is False


def test_experiment_rejects_duplicate_issuer_rows_within_a_window(tmp_path) -> None:
    store = FileTranscriptStore(tmp_path / "transcripts")
    current = (
        _record("AAA", "issuer-a", "2026Q2", 5),
        _record("AAA.B", "issuer-a", "2026Q2", 5),
    )
    baseline = (_record("AAA", "issuer-a", "2026Q1", 2),)

    try:
        run_comparable_cached_experiment(
            current,
            baseline,
            provider="fixture",
            transcript_store=store,
        )
    except ValueError as exc:
        assert "duplicate company_id" in str(exc)
    else:
        raise AssertionError("duplicate company_id should be rejected")
