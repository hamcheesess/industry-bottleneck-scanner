import json
from pathlib import Path

from industry_bottleneck_scanner import phase1_pilot_cli
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


class FakeSource:
    provider_name = "alpha_vantage"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def fetch(self, *, ticker: str, quarter: str):
        evidence = (
            "We reported record backlog, capacity remains constrained, and pricing remains strong."
            if quarter == "2026Q2"
            else "Operations were stable during the quarter."
        )
        return EarningsCallTranscript(
            provider=self.provider_name,
            ticker=ticker,
            fiscal_quarter=quarter,
            turns=(
                TranscriptTurn(speaker="CEO", title="Chief Executive Officer", text=evidence),
                TranscriptTurn(
                    speaker="Operator",
                    title=None,
                    text="We will now begin the question-and-answer session.",
                ),
                TranscriptTurn(speaker="Analyst", title="Analyst", text="Thank you."),
            ),
        )


def _write_requests(path: Path) -> None:
    path.write_text(
        "ticker,quarter\n"
        "AAA,2026Q2\nAAA,2026Q1\n"
        "BBB,2026Q2\nBBB,2026Q1\n"
        "CCC,2026Q2\nCCC,2026Q1\n",
        encoding="utf-8",
    )


def _write_metadata(path: Path, quarter: str, date_prefix: str) -> None:
    path.write_text(
        "ticker,company_id,quarter,published_at,sector,industry,subindustry,published_at_source_url\n"
        f"AAA,issuer-a,{quarter},{date_prefix}T15:00:00+00:00,Industrials,Electrical Equipment,Power,https://example.test/a\n"
        f"BBB,issuer-b,{quarter},{date_prefix}T15:00:00+00:00,Industrials,Electrical Equipment,Protection,https://example.test/b\n"
        f"CCC,issuer-c,{quarter},{date_prefix}T15:00:00+00:00,Industrials,Electrical Equipment,Utility,https://example.test/c\n",
        encoding="utf-8",
    )


def test_phase1_pilot_runs_collection_quality_scan_and_acceleration(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test-key")
    monkeypatch.setattr(phase1_pilot_cli, "AlphaVantageTranscriptSource", FakeSource)

    requests = tmp_path / "requests.csv"
    current = tmp_path / "current.csv"
    baseline = tmp_path / "baseline.csv"
    _write_requests(requests)
    _write_metadata(current, "2026Q2", "2026-07-30")
    _write_metadata(baseline, "2026Q1", "2026-04-30")
    output = tmp_path / "pilot.json"
    artifact_root = tmp_path / "artifacts"

    code = phase1_pilot_cli.main(
        [
            "--requests", str(requests),
            "--current", str(current),
            "--baseline", str(baseline),
            "--transcript-root", str(tmp_path / "transcripts"),
            "--review-queue", str(tmp_path / "review.json"),
            "--max-provider-requests", "6",
            "--interval-seconds", "0",
            "--min-paired-companies", "3",
            "--output", str(output),
            "--artifact-root", str(artifact_root),
        ]
    )

    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "complete"
    assert payload["pilot_diagnostics"]["fully_available_companies"] == 3
    assert payload["pilot_diagnostics"]["transcript_quality"]["qa_detection_rate"] == 1.0
    assert payload["current"]["diagnostics"]["distinct_companies"] == 3
    electrical = next(item for item in payload["acceleration"] if item["bucket"] == "Electrical Equipment")
    assert electrical["aggregation_level"] == "industry"
    assert electrical["triggered"] is True
    assert electrical["confirmed"] is True
    assert (artifact_root / "current_signals.jsonl").exists()
    assert (artifact_root / "baseline_signals.jsonl").exists()
    assert "test-key" not in output.read_text(encoding="utf-8")
