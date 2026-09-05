from industry_bottleneck_scanner.alpha_vantage import TranscriptProviderError
from industry_bottleneck_scanner.transcript_coverage import evaluate_coverage
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


class FakeSource:
    provider_name = "fake"

    def fetch(self, *, ticker: str, quarter: str):
        if ticker == "MISS":
            return None
        if ticker == "RATE":
            raise TranscriptProviderError(
                "Please consider spreading out your free API requests more sparingly "
                "(1 request per second)."
            )
        if ticker == "ERR":
            raise TranscriptProviderError("unexpected provider failure")
        return EarningsCallTranscript(
            provider="fake",
            ticker=ticker,
            fiscal_quarter=quarter,
            turns=(TranscriptTurn(speaker="CEO", title=None, text="text"),),
        )


def test_coverage_summary_distinguishes_statuses() -> None:
    result = evaluate_coverage(
        FakeSource(),
        tickers=["AAA", "MISS", "RATE", "ERR", "BBB"],
        quarter="2026Q2",
    )

    assert result.requested == 5
    assert result.available == 2
    assert result.missing == 1
    assert result.rate_limited == 1
    assert result.errors == 1
    assert result.availability_rate == 0.4
    assert result.resolved_rate == 0.6
    assert [item.status for item in result.results] == [
        "available",
        "missing",
        "rate_limited",
        "provider_error",
        "available",
    ]


def test_coverage_probe_is_request_capped() -> None:
    result = evaluate_coverage(
        FakeSource(),
        tickers=["AAA", "BBB", "CCC"],
        quarter="2026Q2",
        max_requests=2,
    )

    assert result.requested == 2
    assert [item.ticker for item in result.results] == ["AAA", "BBB"]


def test_coverage_probe_waits_between_requests() -> None:
    sleeps: list[float] = []
    result = evaluate_coverage(
        FakeSource(),
        tickers=["AAA", "BBB", "CCC"],
        quarter="2026Q2",
        min_interval_seconds=1.1,
        sleeper=sleeps.append,
    )

    assert result.requested == 3
    assert sleeps == [1.1, 1.1]
