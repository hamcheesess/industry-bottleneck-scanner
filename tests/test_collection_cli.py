import json

from industry_bottleneck_scanner import collection_cli
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


class FakeSource:
    provider_name = "alpha_vantage"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def fetch(self, *, ticker: str, quarter: str):
        return EarningsCallTranscript(
            provider=self.provider_name,
            ticker=ticker,
            fiscal_quarter=quarter,
            turns=(
                TranscriptTurn(speaker="CEO", title="CEO", text="Prepared remarks."),
                TranscriptTurn(
                    speaker="Operator",
                    title=None,
                    text="We will now begin the question-and-answer session.",
                ),
                TranscriptTurn(speaker="Analyst", title="Analyst", text="Question."),
                TranscriptTurn(speaker="CEO", title="CEO", text="Pricing remains strong."),
            ),
        )


def test_collection_cli_embeds_pilot_readiness(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test-key")
    monkeypatch.setattr(collection_cli, "AlphaVantageTranscriptSource", FakeSource)
    requests = tmp_path / "requests.csv"
    requests.write_text(
        "ticker,quarter\n"
        "AAA,2026Q2\nAAA,2026Q1\n"
        "BBB,2026Q2\nBBB,2026Q1\n"
        "CCC,2026Q2\nCCC,2026Q1\n",
        encoding="utf-8",
    )
    output = tmp_path / "collection.json"

    assert collection_cli.main(
        [
            "--requests", str(requests),
            "--transcript-root", str(tmp_path / "transcripts"),
            "--max-provider-requests", "6",
            "--interval-seconds", "0",
            "--output", str(output),
        ]
    ) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["fetched"] == 6
    assert payload["pilot_diagnostics"]["fully_available_companies"] == 3
    assert payload["pilot_diagnostics"]["ready_for_matched_experiment"] is True
    quality = payload["pilot_diagnostics"]["transcript_quality"]
    assert quality["transcript_count"] == 6
    assert quality["qa_detection_rate"] == 1.0
    assert quality["speaker_label_rate"] == 1.0
    assert "test-key" not in output.read_text(encoding="utf-8")
