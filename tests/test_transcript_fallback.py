from dataclasses import dataclass
from pathlib import Path

import pytest

from industry_bottleneck_scanner.alpha_vantage import TranscriptProviderError
from industry_bottleneck_scanner.transcript_fallback import TranscriptFallbackResolver
from industry_bottleneck_scanner.transcript_store import FileTranscriptStore
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


@dataclass
class FakeSource:
    provider_name: str
    payloads: dict[tuple[str, str], EarningsCallTranscript | None | Exception]

    def fetch(self, *, ticker: str, quarter: str):
        value = self.payloads.get((ticker, quarter))
        if isinstance(value, Exception):
            raise value
        return value


def transcript(provider: str, ticker: str, quarter: str, text: str) -> EarningsCallTranscript:
    return EarningsCallTranscript(
        provider=provider,
        ticker=ticker,
        fiscal_quarter=quarter,
        turns=(TranscriptTurn(speaker="CEO", title="CEO", text=text),),
    )


def test_resolver_falls_back_for_entire_issuer_pair_not_just_missing_quarter(tmp_path: Path) -> None:
    primary = FakeSource(
        "alpha_vantage",
        {
            ("AAA", "2026Q1"): transcript("alpha_vantage", "AAA", "2026Q1", "primary baseline"),
            ("AAA", "2026Q2"): None,
        },
    )
    fallback = FakeSource(
        "quartr_edited",
        {
            ("AAA", "2026Q1"): transcript("quartr_edited", "AAA", "2026Q1", "fallback baseline"),
            ("AAA", "2026Q2"): transcript("quartr_edited", "AAA", "2026Q2", "fallback current"),
        },
    )
    store = FileTranscriptStore(tmp_path)
    resolved = TranscriptFallbackResolver((primary, fallback)).resolve_issuer_windows(
        store=store,
        ticker="AAA",
        quarters=("2026Q1", "2026Q2"),
    )

    assert resolved is not None
    assert resolved.provider == "quartr_edited"
    assert [item.provider for item in resolved.transcripts] == ["quartr_edited", "quartr_edited"]
    assert resolved.by_quarter()["2026Q1"].full_text == "fallback baseline"
    assert [(item.provider, item.quarter, item.status) for item in resolved.attempts] == [
        ("alpha_vantage", "2026Q1", "fetched"),
        ("alpha_vantage", "2026Q2", "missing"),
        ("quartr_edited", "2026Q1", "fetched"),
        ("quartr_edited", "2026Q2", "fetched"),
    ]


def test_resolver_uses_primary_when_primary_pair_is_complete(tmp_path: Path) -> None:
    primary = FakeSource(
        "alpha_vantage",
        {
            ("AAA", "2026Q1"): transcript("alpha_vantage", "AAA", "2026Q1", "baseline"),
            ("AAA", "2026Q2"): transcript("alpha_vantage", "AAA", "2026Q2", "current"),
        },
    )
    fallback = FakeSource("quartr_edited", {})

    resolved = TranscriptFallbackResolver((primary, fallback)).resolve_issuer_windows(
        store=FileTranscriptStore(tmp_path),
        ticker="AAA",
        quarters=("2026Q1", "2026Q2"),
    )

    assert resolved is not None
    assert resolved.provider == "alpha_vantage"
    assert not any(item.provider == "quartr_edited" for item in resolved.attempts)


def test_resolver_stops_on_provider_error_instead_of_silently_switching(tmp_path: Path) -> None:
    primary = FakeSource(
        "alpha_vantage",
        {
            ("AAA", "2026Q1"): TranscriptProviderError("rate limit"),
        },
    )
    fallback = FakeSource(
        "quartr_edited",
        {
            ("AAA", "2026Q1"): transcript("quartr_edited", "AAA", "2026Q1", "fallback"),
        },
    )

    with pytest.raises(TranscriptProviderError):
        TranscriptFallbackResolver((primary, fallback)).resolve_issuer_windows(
            store=FileTranscriptStore(tmp_path),
            ticker="AAA",
            quarters=("2026Q1",),
        )


def test_resolver_requires_multiple_unique_sources() -> None:
    source = FakeSource("alpha_vantage", {})
    with pytest.raises(ValueError, match="at least two"):
        TranscriptFallbackResolver((source,))
    with pytest.raises(ValueError, match="duplicate"):
        TranscriptFallbackResolver((source, FakeSource("alpha_vantage", {})))
