from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .alpha_vantage import TranscriptProviderError
from .transcripts import TranscriptSource


@dataclass(frozen=True)
class CoverageResult:
    ticker: str
    quarter: str
    status: str
    turn_count: int = 0
    error: str | None = None


@dataclass(frozen=True)
class CoverageSummary:
    requested: int
    available: int
    missing: int
    errors: int
    results: tuple[CoverageResult, ...]

    @property
    def availability_rate(self) -> float:
        return 0.0 if self.requested == 0 else self.available / self.requested


def evaluate_coverage(
    source: TranscriptSource,
    *,
    tickers: Iterable[str],
    quarter: str,
    max_requests: int | None = None,
) -> CoverageSummary:
    """Measure provider availability on a bounded ticker sample.

    This function is deliberately request-capped. Coverage experiments must start with a
    small representative sample before any universe-scale collection is attempted.
    """

    results: list[CoverageResult] = []
    for index, ticker in enumerate(tickers):
        if max_requests is not None and index >= max_requests:
            break
        try:
            transcript = source.fetch(ticker=ticker, quarter=quarter)
        except TranscriptProviderError as exc:
            results.append(
                CoverageResult(
                    ticker=ticker,
                    quarter=quarter,
                    status="error",
                    error=str(exc),
                )
            )
            continue

        if transcript is None:
            results.append(CoverageResult(ticker=ticker, quarter=quarter, status="missing"))
            continue

        results.append(
            CoverageResult(
                ticker=ticker,
                quarter=quarter,
                status="available",
                turn_count=len(transcript.turns),
            )
        )

    return CoverageSummary(
        requested=len(results),
        available=sum(result.status == "available" for result in results),
        missing=sum(result.status == "missing" for result in results),
        errors=sum(result.status == "error" for result in results),
        results=tuple(results),
    )
