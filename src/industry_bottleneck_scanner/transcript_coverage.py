from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Iterable

from .alpha_vantage import TranscriptProviderError
from .transcripts import TranscriptSource

Sleeper = Callable[[float], None]


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
    rate_limited: int
    errors: int
    results: tuple[CoverageResult, ...]

    @property
    def availability_rate(self) -> float:
        return 0.0 if self.requested == 0 else self.available / self.requested

    @property
    def resolved_rate(self) -> float:
        resolved = self.available + self.missing
        return 0.0 if self.requested == 0 else resolved / self.requested


def _classify_provider_error(message: str) -> str:
    normalized = message.casefold()
    rate_limit_markers = (
        "1 request per second",
        "rate limit",
        "rate-limit",
        "too many requests",
        "requests more sparingly",
        "25 requests per day",
    )
    if any(marker in normalized for marker in rate_limit_markers):
        return "rate_limited"
    return "provider_error"


def evaluate_coverage(
    source: TranscriptSource,
    *,
    tickers: Iterable[str],
    quarter: str,
    max_requests: int | None = None,
    min_interval_seconds: float = 0.0,
    sleeper: Sleeper = time.sleep,
) -> CoverageSummary:
    """Measure provider availability on a bounded ticker sample.

    The probe is deliberately request-capped. A minimum interval can be enforced between
    provider calls so free-tier rate limits do not masquerade as missing coverage.
    """

    if min_interval_seconds < 0:
        raise ValueError("min_interval_seconds must be non-negative")

    results: list[CoverageResult] = []
    for index, ticker in enumerate(tickers):
        if max_requests is not None and index >= max_requests:
            break
        if results and min_interval_seconds:
            sleeper(min_interval_seconds)

        try:
            transcript = source.fetch(ticker=ticker, quarter=quarter)
        except TranscriptProviderError as exc:
            message = str(exc)
            results.append(
                CoverageResult(
                    ticker=ticker,
                    quarter=quarter,
                    status=_classify_provider_error(message),
                    error=message,
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
        rate_limited=sum(result.status == "rate_limited" for result in results),
        errors=sum(result.status == "provider_error" for result in results),
        results=tuple(results),
    )
