import csv
import json
from pathlib import Path

from industry_bottleneck_scanner import validation_collection_cli
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
            turns=(TranscriptTurn(speaker="CEO", title="Chief Executive Officer", text="Stable operations."),),
        )


def _write_requests(path: Path, rows: list[tuple[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("ticker", "quarter"))
        writer.writerows(rows)


def test_validation_collection_dedupes_and_resumes_from_cache(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test-key")
    monkeypatch.setattr(validation_collection_cli, "AlphaVantageTranscriptSource", FakeSource)

    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    _write_requests(first, [("AAA", "2021Q2"), ("AAA", "2021Q1")])
    _write_requests(second, [("AAA", "2021Q2"), ("BBB", "2021Q2")])
    monkeypatch.setattr(validation_collection_cli, "DEFAULT_REQUEST_FILES", (first, second))

    transcript_root = tmp_path / "transcripts"
    output = tmp_path / "status.json"
    missing_blind = tmp_path / "no-blind.csv"

    code = validation_collection_cli.main(
        [
            "--transcript-root", str(transcript_root),
            "--blind-requests", str(missing_blind),
            "--max-provider-requests", "10",
            "--interval-seconds", "0",
            "--output", str(output),
        ]
    )
    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["planned_unique_requests"] == 3
    assert payload["available_after_run"] == 3
    assert payload["run"]["provider_requests"] == 3
    assert payload["blind_requests_included"] is False

    code = validation_collection_cli.main(
        [
            "--transcript-root", str(transcript_root),
            "--blind-requests", str(missing_blind),
            "--max-provider-requests", "10",
            "--interval-seconds", "0",
            "--output", str(output),
        ]
    )
    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["run"]["provider_requests"] == 0
    assert payload["run"]["cache_hits"] == 3
