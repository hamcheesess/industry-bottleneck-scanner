from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .alpha_vantage import TranscriptProviderError
from .transcript_store import FileTranscriptStore
from .transcripts import EarningsCallTranscript, TranscriptSource
from .universe import normalize_ticker


@dataclass(frozen=True)
class ProviderAttempt:
    provider: str
    quarter: str
    status: str
    from_cache: bool = False


@dataclass(frozen=True)
class ResolvedTranscriptSet:
    ticker: str
    provider: str
    quarters: tuple[str, ...]
    transcripts: tuple[EarningsCallTranscript, ...]
    attempts: tuple[ProviderAttempt, ...]

    def by_quarter(self) -> dict[str, EarningsCallTranscript]:
        return {item.fiscal_quarter: item for item in self.transcripts}


class TranscriptFallbackResolver:
    """Resolve comparable issuer windows from a predeclared provider hierarchy.

    A provider is accepted only if it can supply *every* requested quarter for the issuer.
    This prevents a current window from using one transcript vendor while its baseline uses
    another, which could manufacture apparent acceleration from provider-format differences.

    Fallback occurs only after an explicit provider miss. Provider errors and rate limits stop
    the chain instead of silently changing source. Provider-specific cache entries remain
    separate and preserve their original provenance.
    """

    def __init__(self, sources: Iterable[TranscriptSource]) -> None:
        self.sources = tuple(sources)
        if len(self.sources) < 2:
            raise ValueError("multi-source fallback requires at least two ordered transcript sources")
        names = [source.provider_name for source in self.sources]
        if len(set(names)) != len(names):
            raise ValueError("provider hierarchy contains duplicate provider names")

    def resolve_issuer_windows(
        self,
        *,
        store: FileTranscriptStore,
        ticker: str,
        quarters: Iterable[str],
    ) -> ResolvedTranscriptSet | None:
        symbol = normalize_ticker(ticker)
        normalized_quarters = tuple(dict.fromkeys(str(value).strip().upper() for value in quarters))
        if not symbol:
            raise ValueError("ticker is required")
        if not normalized_quarters:
            raise ValueError("at least one quarter is required")

        attempts: list[ProviderAttempt] = []
        for source in self.sources:
            provider = source.provider_name
            provider_transcripts: list[EarningsCallTranscript] = []
            provider_complete = True

            for quarter in normalized_quarters:
                cached = store.load(provider=provider, ticker=symbol, quarter=quarter)
                if cached is not None:
                    provider_transcripts.append(cached)
                    attempts.append(
                        ProviderAttempt(provider=provider, quarter=quarter, status="cache_hit", from_cache=True)
                    )
                    continue

                try:
                    transcript = source.fetch(ticker=symbol, quarter=quarter)
                except TranscriptProviderError:
                    attempts.append(ProviderAttempt(provider=provider, quarter=quarter, status="error"))
                    raise

                if transcript is None:
                    attempts.append(ProviderAttempt(provider=provider, quarter=quarter, status="missing"))
                    provider_complete = False
                    break

                if transcript.provider != provider:
                    raise ValueError(
                        f"source {provider!r} returned transcript labeled as {transcript.provider!r}"
                    )
                if transcript.ticker != symbol or transcript.fiscal_quarter != quarter:
                    raise ValueError("transcript source returned mismatched ticker/quarter identity")
                store.save(transcript)
                provider_transcripts.append(transcript)
                attempts.append(ProviderAttempt(provider=provider, quarter=quarter, status="fetched"))

            if provider_complete and len(provider_transcripts) == len(normalized_quarters):
                by_quarter = {item.fiscal_quarter: item for item in provider_transcripts}
                ordered = tuple(by_quarter[quarter] for quarter in normalized_quarters)
                return ResolvedTranscriptSet(
                    ticker=symbol,
                    provider=provider,
                    quarters=normalized_quarters,
                    transcripts=ordered,
                    attempts=tuple(attempts),
                )

        return None
