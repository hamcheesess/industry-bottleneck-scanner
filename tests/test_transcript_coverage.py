from industry_bottleneck_scanner.alpha_vantage import TranscriptProviderError
from industry_bottleneck_scanner.transcript_coverage import evaluate_coverage
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


class FakeSource:
    provider_name = "fake"

    def fetch(self, *, ticker: str, quarter: str):
        if ticker == "MISS":
            return None
        if ticker == "ERR":
            raise TranscriptProviderError("rate limited")
        return EarningsCallTranscript(
            provider="fake",
            ticker=ticker,
            fiscal_quarter=quarter,
            turns=(TranscriptTurn(speaker="CEO", title=None, text="text"),),
        )


def test_coverage_summary_distinguishes_available_missing_and_error() -> None:
    result = evaluate_coverage(
        FakeSource(),
        tickers=["AAA", "MISS", "ERR", "BBB"],
        quarter="2026Q2",
    )

    assert result.requested == 4
    assert result.available == 2
    assert result.missing == 1
    assert result.errors == 1
    assert result.availability_rate == 0.5


def test_coverage_probe_is_request_capped() -> None:
    result = evaluate_coverage(
        FakeSource(),
        tickers=["AAA", "BBB", "CCC"],
        quarter="2026Q2",
        max_requests=2,
    )

    assert result.requested == 2
    assert [item.ticker for item in result.results] == ["AAA", "BBB"]
