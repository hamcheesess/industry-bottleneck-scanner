from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .alpha_vantage import TranscriptProviderError
from .transcript_store import FileTranscriptStore
from .transcripts import EarningsCallTranscript, TranscriptSource


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


def collect_transcripts(
    source: TranscriptSource,
    *,
    store: FileTranscriptStore,
    tickers: Iterable[str],
    quarter: str,
    max_provider_requests: int = 25,
) -> CollectionSummary:
    """Fetch transcripts incrementally with cache-first, request-capped behavior.

    Cached transcripts never consume provider requests. New provider requests stop once
    ``max_provider_requests`` has been reached. This makes repeated runs resumable and
    prevents accidental universe-scale backfills from exhausting a provider quota.
    """

    if max_provider_requests < 0:
        raise ValueError("max_provider_requests must be non-negative")

    items: list[CollectionItem] = []
    provider_requests = 0
    provider = source.provider_name
    normalized_quarter = quarter.upper()

    for ticker in tickers:
        cached = store.load(provider=provider, ticker=ticker, quarter=normalized_quarter)
        if cached is not None:
            items.append(
                CollectionItem(
                    ticker=ticker,
                    quarter=normalized_quarter,
                    status="cache_hit",
                    turn_count=len(cached.turns),
                )
            )
            continue

        if provider_requests >= max_provider_requests:
            items.append(
                CollectionItem(
                    ticker=ticker,
                    quarter=normalized_quarter,
                    status="budget_exhausted",
                )
            )
            continue

        provider_requests += 1
        try:
            transcript: EarningsCallTranscript | None = source.fetch(
                ticker=ticker,
                quarter=normalized_quarter,
            )
        except TranscriptProviderError as exc:
            message = str(exc)
            status = _error_status(message)
            items.append(
                CollectionItem(
                    ticker=ticker,
                    quarter=normalized_quarter,
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
                    ticker=ticker,
                    quarter=normalized_quarter,
                    status="missing",
                )
            )
            continue

        store.save(transcript)
        items.append(
            CollectionItem(
                ticker=ticker,
                quarter=normalized_quarter,
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
