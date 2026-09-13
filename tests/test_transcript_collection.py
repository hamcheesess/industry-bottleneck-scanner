from pathlib import Path

from industry_bottleneck_scanner.alpha_vantage import TranscriptProviderError
from industry_bottleneck_scanner.transcript_collection import collect_transcripts
from industry_bottleneck_scanner.transcript_store import FileTranscriptStore
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


class FakeSource:
    provider_name = "fake"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def fetch(self, *, ticker: str, quarter: str):
        self.calls.append((ticker, quarter))
        if ticker == "MISS":
            return None
        if ticker == "LIMIT":
            raise TranscriptProviderError("Please use 1 request per second; rate limit reached")
        if ticker == "ERR":
            raise TranscriptProviderError("provider failure")
        return EarningsCallTranscript(
            provider="fake",
            ticker=ticker,
            fiscal_quarter=quarter,
            turns=(TranscriptTurn(speaker="CEO", title=None, text=f"{ticker} text"),),
        )


def test_collection_is_cache_first_and_resumable(tmp_path: Path) -> None:
    store = FileTranscriptStore(tmp_path)
    source = FakeSource()

    first = collect_transcripts(
        source,
        store=store,
        tickers=["AAA", "BBB"],
        quarter="2026Q2",
        max_provider_requests=2,
    )
    second = collect_transcripts(
        source,
        store=store,
        tickers=["AAA", "BBB"],
        quarter="2026Q2",
        max_provider_requests=2,
    )

    assert first.fetched == 2
    assert first.provider_requests == 2
    assert second.cache_hits == 2
    assert second.provider_requests == 0
    assert source.calls == [("AAA", "2026Q2"), ("BBB", "2026Q2")]


def test_collection_respects_provider_budget(tmp_path: Path) -> None:
    summary = collect_transcripts(
        FakeSource(),
        store=FileTranscriptStore(tmp_path),
        tickers=["AAA", "BBB", "CCC"],
        quarter="2026Q2",
        max_provider_requests=2,
    )

    assert summary.provider_requests == 2
    assert [item.status for item in summary.items] == ["fetched", "fetched", "budget_exhausted"]


def test_collection_stops_on_rate_limit(tmp_path: Path) -> None:
    source = FakeSource()
    summary = collect_transcripts(
        source,
        store=FileTranscriptStore(tmp_path),
        tickers=["AAA", "LIMIT", "BBB"],
        quarter="2026Q2",
        max_provider_requests=3,
    )

    assert summary.fetched == 1
    assert summary.rate_limited == 1
    assert source.calls == [("AAA", "2026Q2"), ("LIMIT", "2026Q2")]


def test_collection_distinguishes_missing_and_provider_error(tmp_path: Path) -> None:
    summary = collect_transcripts(
        FakeSource(),
        store=FileTranscriptStore(tmp_path),
        tickers=["MISS", "ERR"],
        quarter="2026Q2",
        max_provider_requests=2,
    )

    assert summary.missing == 1
    assert summary.errors == 1
