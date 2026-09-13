from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Iterable

from .alpha_vantage import TranscriptProviderError
from .transcript_store import FileTranscriptStore
from .transcripts import EarningsCallTranscript, TranscriptSource
from .universe import normalize_ticker

Sleeper = Callable[[float], None]


@dataclass(frozen=True)
class TranscriptRequest:
    ticker: str
    quarter: str

    def __post_init__(self) -> None:
        ticker = normalize_ticker(self.ticker)
        quarter = self.quarter.strip().upper()
        if not ticker:
            raise ValueError("ticker is required")
        if len(quarter) != 6 or quarter[4] != "Q" or quarter[5] not in "1234":
            raise ValueError("quarter must use YYYYQ# format")
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "quarter", quarter)


@dataclass(frozen=True)
class CollectionItem:
    ticker: str
    quarter: str
    status: str
    turn_count: int = 0
    error: str | None = None


@dataclass(frozen=True)
class CollectionSummary:
    requested: int
    cache_hits: int
    fetched: int
    missing: int
    rate_limited: int
    errors: int
    provider_requests: int
    items: tuple[CollectionItem, ...]


def _error_status(message: str) -> str:
    lowered = message.casefold()
    if "request per second" in lowered or "rate limit" in lowered or "25 requests per day" in lowered:
        return "rate_limited"
    return "error"


def collect_requested_transcripts(
    source: TranscriptSource,
    *,
    store: FileTranscriptStore,
    requests: Iterable[TranscriptRequest],
    max_provider_requests: int = 25,
    min_interval_seconds: float = 0.0,
    sleeper: Sleeper = time.sleep,
) -> CollectionSummary:
    """Fetch an explicit sequence of ticker/fiscal-quarter pairs cache-first.

    Per-company fiscal quarters avoid treating a single calendar-quarter label as if it
    meant the same fiscal period for every issuer. Cached requests consume no provider
    budget. A provider rate-limit response stops the run so a retry storm cannot occur.
    """

    if max_provider_requests < 0:
        raise ValueError("max_provider_requests must be non-negative")
    if min_interval_seconds < 0:
        raise ValueError("min_interval_seconds must be non-negative")

    items: list[CollectionItem] = []
    provider_requests = 0
    provider = source.provider_name

    for request in requests:
        cached = store.load(provider=provider, ticker=request.ticker, quarter=request.quarter)
        if cached is not None:
            items.append(
                CollectionItem(
                    ticker=request.ticker,
                    quarter=request.quarter,
                    status="cache_hit",
                    turn_count=len(cached.turns),
                )
            )
            continue

        if provider_requests >= max_provider_requests:
            items.append(
                CollectionItem(
                    ticker=request.ticker,
                    quarter=request.quarter,
                    status="budget_exhausted",
                )
            )
            continue

        if provider_requests and min_interval_seconds:
            sleeper(min_interval_seconds)
        provider_requests += 1
        try:
            transcript: EarningsCallTranscript | None = source.fetch(
                ticker=request.ticker,
                quarter=request.quarter,
            )
        except TranscriptProviderError as exc:
            message = str(exc)
            status = _error_status(message)
            items.append(
                CollectionItem(
                    ticker=request.ticker,
                    quarter=request.quarter,
                    status=status,
                    error=message,
                )
            )
            if status == "rate_limited":
                break
            continue

        if transcript is None:
            items.append(
                CollectionItem(
                    ticker=request.ticker,
                    quarter=request.quarter,
                    status="missing",
                )
            )
            continue

        store.save(transcript)
        items.append(
            CollectionItem(
                ticker=request.ticker,
                quarter=request.quarter,
                status="fetched",
                turn_count=len(transcript.turns),
            )
        )

    return CollectionSummary(
        requested=len(items),
        cache_hits=sum(item.status == "cache_hit" for item in items),
        fetched=sum(item.status == "fetched" for item in items),
        missing=sum(item.status == "missing" for item in items),
        rate_limited=sum(item.status == "rate_limited" for item in items),
        errors=sum(item.status == "error" for item in items),
        provider_requests=provider_requests,
        items=tuple(items),
    )


def collect_transcripts(
    source: TranscriptSource,
    *,
    store: FileTranscriptStore,
    tickers: Iterable[str],
    quarter: str,
    max_provider_requests: int = 25,
) -> CollectionSummary:
    """Compatibility wrapper for a same-quarter request batch."""

    requests = tuple(TranscriptRequest(ticker=ticker, quarter=quarter) for ticker in tickers)
    return collect_requested_transcripts(
        source,
        store=store,
        requests=requests,
        max_provider_requests=max_provider_requests,
    )
