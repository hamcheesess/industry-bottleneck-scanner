from industry_bottleneck_scanner.alpha_vantage import TranscriptProviderError
from industry_bottleneck_scanner.quartr import QuartrTranscriptSource


def test_quartr_uses_header_auth_and_normalizes_edited_speaker_roles() -> None:
    seen: dict[str, object] = {}

    def metadata_transport(url, headers):
        seen["url"] = url
        seen["headers"] = headers
        return {
            "data": [
                {
                    "id": 10,
                    "typeId": 22,
                    "updatedAt": "2026-08-01T12:00:00Z",
                    "fileUrl": "https://cdn.example/transcript.json",
                    "event": {
                        "fiscalYear": 2026,
                        "fiscalPeriod": "Q2",
                        "language": "en",
                    },
                }
            ]
        }

    def file_transport(url):
        assert url == "https://cdn.example/transcript.json"
        return {
            "speaker_mapping": [
                {"speaker": 0, "speaker_data": {"name": "Jane CEO", "role": "CEO", "company": "Example Inc."}},
                {"speaker": 1, "speaker_data": {"name": "Alex Analyst", "role": "Analyst", "company": "Research Bank"}},
            ],
            "transcript": {
                "paragraphs": [
                    {"speaker": 0, "text": "Capacity remains constrained."},
                    {"speaker": 1, "text": "Are lead times still long?"},
                ]
            },
        }

    source = QuartrTranscriptSource(
        api_key="secret-key",
        metadata_transport=metadata_transport,
        file_transport=file_transport,
    )
    transcript = source.fetch(ticker="aapl", quarter="2026Q2")

    assert transcript is not None
    assert transcript.provider == "quartr_edited"
    assert transcript.ticker == "AAPL"
    assert transcript.source_url == "https://cdn.example/transcript.json"
    assert transcript.turns[0].title == "CEO | Example Inc."
    assert transcript.turns[1].title == "Analyst | Research Bank"
    assert "secret-key" not in str(seen["url"])
    assert seen["headers"]["x-api-key"] == "secret-key"
    assert "typeIds=22" in str(seen["url"])


def test_quartr_does_not_treat_raw_transcript_as_edited_fallback() -> None:
    source = QuartrTranscriptSource(
        api_key="key",
        metadata_transport=lambda url, headers: {
            "data": [
                {
                    "id": 9,
                    "typeId": 15,
                    "fileUrl": "https://cdn.example/raw.json",
                    "event": {"fiscalYear": 2026, "fiscalPeriod": "Q2", "language": "en"},
                }
            ]
        },
        file_transport=lambda url: {},
    )

    assert source.fetch(ticker="AAPL", quarter="2026Q2") is None


def test_quartr_rejects_role_unsafe_edited_payload() -> None:
    source = QuartrTranscriptSource(
        api_key="key",
        metadata_transport=lambda url, headers: {
            "data": [
                {
                    "id": 10,
                    "typeId": 22,
                    "fileUrl": "https://cdn.example/edited.json",
                    "event": {"fiscalYear": 2026, "fiscalPeriod": "Q2", "language": "en"},
                }
            ]
        },
        file_transport=lambda url: {"transcript": {"paragraphs": [{"speaker": 0, "text": "hello"}]}},
    )

    try:
        source.fetch(ticker="AAPL", quarter="2026Q2")
    except TranscriptProviderError as exc:
        assert "speaker_mapping" in str(exc)
    else:  # pragma: no cover - safety assertion
        raise AssertionError("role-unsafe edited transcript must be rejected")
