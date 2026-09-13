from industry_bottleneck_scanner.transcript_collection import (
    TranscriptRequest,
    collect_requested_transcripts,
)
from industry_bottleneck_scanner.transcript_store import FileTranscriptStore
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


class FakeSource:
    provider_name = "fixture"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def fetch(self, *, ticker: str, quarter: str):
        self.calls.append((ticker, quarter))
        return EarningsCallTranscript(
            provider="fixture",
            ticker=ticker,
            fiscal_quarter=quarter,
            turns=(TranscriptTurn(speaker="CEO", title="CEO", text="text"),),
        )


def test_explicit_requests_preserve_company_specific_fiscal_quarters(tmp_path) -> None:
    source = FakeSource()
    sleeps: list[float] = []
    summary = collect_requested_transcripts(
        source,
        store=FileTranscriptStore(tmp_path),
        requests=(
            TranscriptRequest("AAA", "2026Q2"),
            TranscriptRequest("BBB", "2026Q1"),
            TranscriptRequest("CCC", "2025Q4"),
        ),
        max_provider_requests=3,
        min_interval_seconds=1.1,
        sleeper=sleeps.append,
    )

    assert source.calls == [("AAA", "2026Q2"), ("BBB", "2026Q1"), ("CCC", "2025Q4")]
    assert sleeps == [1.1, 1.1]
    assert summary.fetched == 3
    assert summary.provider_requests == 3


def test_cached_explicit_request_does_not_consume_budget_or_sleep(tmp_path) -> None:
    store = FileTranscriptStore(tmp_path)
    store.save(
        EarningsCallTranscript(
            provider="fixture",
            ticker="AAA",
            fiscal_quarter="2026Q2",
            turns=(TranscriptTurn(speaker="CEO", title="CEO", text="cached"),),
        )
    )
    source = FakeSource()
    sleeps: list[float] = []

    summary = collect_requested_transcripts(
        source,
        store=store,
        requests=(TranscriptRequest("AAA", "2026Q2"), TranscriptRequest("BBB", "2026Q1")),
        max_provider_requests=1,
        min_interval_seconds=1.1,
        sleeper=sleeps.append,
    )

    assert summary.cache_hits == 1
    assert summary.fetched == 1
    assert summary.provider_requests == 1
    assert source.calls == [("BBB", "2026Q1")]
    assert sleeps == []
