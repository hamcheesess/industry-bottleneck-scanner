from industry_bottleneck_scanner.roic import RoicTranscriptSource


def test_roic_resolves_us_listing_and_preserves_analyst_speaker_provenance() -> None:
    seen: list[str] = []

    def transport(url: str):
        seen.append(url)
        if "/v2/tickers/search" in url:
            return [
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "exchange": "NASDAQ",
                    "exchange_name": "NASDAQ Global Select",
                    "type": "Common Stock",
                }
            ]
        assert "/v3.0.0/earnings-calls/NASDAQ:AAPL?" in url
        return {
            "id": "ecall_example",
            "symbol": "NASDAQ:AAPL",
            "fiscal_year": 2026,
            "fiscal_quarter": 2,
            "date": "2026-05-01",
            "transcript": [
                {"speaker": "Tim Cook", "text": "Demand remains strong."},
                {"speaker": "Analyst - Morgan Stanley", "text": "Are lead times still long?"},
            ],
        }

    source = RoicTranscriptSource(api_key="free-key", transport=transport)
    transcript = source.fetch(ticker="aapl", quarter="2026Q2")

    assert transcript is not None
    assert transcript.provider == "roic_ai"
    assert transcript.ticker == "AAPL"
    assert transcript.fiscal_quarter == "2026Q2"
    assert transcript.turns[0].speaker == "Tim Cook"
    assert transcript.turns[0].title is None
    assert transcript.turns[1].speaker == "Analyst - Morgan Stanley"
    assert transcript.turns[1].title == "Analyst"
    assert "free-key" not in str(transcript.source_url)
    assert any("apikey=free-key" in url for url in seen)


def test_roic_returns_none_when_exact_ticker_is_not_found() -> None:
    source = RoicTranscriptSource(
        api_key="key",
        transport=lambda url: [
            {"symbol": "AAPLX", "exchange": "NASDAQ", "name": "Not Apple"},
        ],
    )

    assert source.fetch(ticker="AAPL", quarter="2026Q2") is None


def test_roic_returns_none_for_missing_transcript() -> None:
    def transport(url: str):
        if "/v2/tickers/search" in url:
            return [{"symbol": "AAA", "exchange": "NYSE", "name": "AAA Inc."}]
        return {"_not_found": True}

    source = RoicTranscriptSource(api_key="key", transport=transport)
    assert source.fetch(ticker="AAA", quarter="2026Q2") is None


def test_roic_prefers_us_exchange_for_duplicate_symbol() -> None:
    def transport(url: str):
        if "/v2/tickers/search" in url:
            return [
                {"symbol": "AAA", "exchange": "LSE", "name": "AAA plc"},
                {"symbol": "AAA", "exchange": "NYSE", "name": "AAA Inc."},
            ]
        assert "/NYSE:AAA?" in url
        return {
            "transcript": [{"speaker": "CEO", "text": "Capacity is constrained."}],
        }

    source = RoicTranscriptSource(api_key="key", transport=transport)
    transcript = source.fetch(ticker="AAA", quarter="2026Q2")
    assert transcript is not None
    assert transcript.full_text == "Capacity is constrained."
