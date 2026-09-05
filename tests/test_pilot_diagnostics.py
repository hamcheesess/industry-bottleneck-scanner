from industry_bottleneck_scanner.pilot_diagnostics import diagnose_pilot
from industry_bottleneck_scanner.transcript_collection import CollectionItem, TranscriptRequest
from industry_bottleneck_scanner.transcript_store import FileTranscriptStore
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


def _save(store: FileTranscriptStore, ticker: str, quarter: str, turns: int = 2) -> None:
    store.save(
        EarningsCallTranscript(
            provider="alpha_vantage",
            ticker=ticker,
            fiscal_quarter=quarter,
            turns=tuple(
                TranscriptTurn(speaker="CEO", title="CEO", text=f"turn {index}")
                for index in range(turns)
            ),
        )
    )


def test_pilot_requires_complete_matched_pairs(tmp_path) -> None:
    store = FileTranscriptStore(tmp_path / "transcripts")
    requests = tuple(
        TranscriptRequest(ticker=ticker, quarter=quarter)
        for ticker in ("AAA", "BBB", "CCC")
        for quarter in ("2026Q2", "2026Q1")
    )
    items = []
    for request in requests:
        _save(store, request.ticker, request.quarter)
        items.append(CollectionItem(request.ticker, request.quarter, "fetched", turn_count=2))

    result = diagnose_pilot(
        provider="alpha_vantage",
        requests=requests,
        items=tuple(items),
        transcript_store=store,
        min_paired_companies=3,
    )

    assert result.available_pairs == 6
    assert result.fully_available_companies == 3
    assert result.ready_for_matched_experiment is True
    assert result.unresolved_pairs == ()
    assert result.average_turns_available == 2.0


def test_rate_limited_pair_blocks_readiness(tmp_path) -> None:
    store = FileTranscriptStore(tmp_path / "transcripts")
    requests = (
        TranscriptRequest("AAA", "2026Q2"),
        TranscriptRequest("AAA", "2026Q1"),
    )
    _save(store, "AAA", "2026Q2")
    items = (
        CollectionItem("AAA", "2026Q2", "fetched", turn_count=2),
        CollectionItem("AAA", "2026Q1", "rate_limited", error="rate limit"),
    )

    result = diagnose_pilot(
        provider="alpha_vantage",
        requests=requests,
        items=items,
        transcript_store=store,
        min_paired_companies=1,
    )

    assert result.available_pairs == 1
    assert result.resolved_pairs == 1
    assert result.unresolved_pairs == (("AAA", "2026Q1"),)
    assert result.ready_for_matched_experiment is False


def test_missing_is_resolved_but_not_available(tmp_path) -> None:
    result = diagnose_pilot(
        provider="alpha_vantage",
        requests=(TranscriptRequest("AAA", "2026Q2"),),
        items=(CollectionItem("AAA", "2026Q2", "missing"),),
        transcript_store=FileTranscriptStore(tmp_path / "transcripts"),
        min_paired_companies=1,
    )

    assert result.resolved_pairs == 1
    assert result.missing_pairs == 1
    assert result.available_pairs == 0
    assert result.ready_for_matched_experiment is False
