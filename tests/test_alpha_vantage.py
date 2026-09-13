from urllib.parse import parse_qs, urlparse

import pytest

from industry_bottleneck_scanner.alpha_vantage import (
    AlphaVantageTranscriptSource,
    TranscriptProviderError,
)


def test_build_url_uses_documented_endpoint_contract() -> None:
    source = AlphaVantageTranscriptSource(api_key="secret", transport=lambda _: {})
    url = source.build_url(ticker="brk.b", quarter="2026q2")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert query["function"] == ["EARNINGS_CALL_TRANSCRIPT"]
    assert query["symbol"] == ["BRK-B"]
    assert query["quarter"] == ["2026Q2"]
    assert query["apikey"] == ["secret"]


def test_fetch_normalizes_turns_without_network_calls() -> None:
    payload = {
        "transcript": [
            {
                "speaker": "Jane Doe",
                "title": "Chief Executive Officer",
                "content": "Demand continues to exceed available capacity.",
                "sentiment": "0.72",
            },
            {
                "speaker": "Analyst",
                "role": "Analyst",
                "speech": "How long are lead times?",
            },
        ]
    }
    source = AlphaVantageTranscriptSource(api_key="secret", transport=lambda _: payload)

    result = source.fetch(ticker="TEST", quarter="2026Q2")

    assert result is not None
    assert result.provider == "alpha_vantage"
    assert result.ticker == "TEST"
    assert len(result.turns) == 2
    assert result.turns[0].speaker == "Jane Doe"
    assert result.turns[0].sentiment == 0.72
    assert "available capacity" in result.full_text


def test_fetch_returns_none_when_provider_has_no_transcript() -> None:
    source = AlphaVantageTranscriptSource(
        api_key="secret",
        transport=lambda _: {"transcript": []},
    )

    assert source.fetch(ticker="TEST", quarter="2026Q2") is None


def test_provider_limit_message_is_explicit_error() -> None:
    source = AlphaVantageTranscriptSource(
        api_key="secret",
        transport=lambda _: {"Note": "API call frequency limit reached"},
    )

    with pytest.raises(TranscriptProviderError, match="frequency limit"):
        source.fetch(ticker="TEST", quarter="2026Q2")


@pytest.mark.parametrize("quarter", ["2026", "2026Q5", "2009Q4", "bad"])
def test_invalid_quarter_is_rejected(quarter: str) -> None:
    source = AlphaVantageTranscriptSource(api_key="secret", transport=lambda _: {})

    with pytest.raises(ValueError):
        source.fetch(ticker="TEST", quarter=quarter)
