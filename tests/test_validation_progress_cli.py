import csv
import json
from pathlib import Path

from industry_bottleneck_scanner import validation_progress_cli
from industry_bottleneck_scanner.transcript_store import FileTranscriptStore
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn
from industry_bottleneck_scanner.validation_progress_cli import ValidationCaseSpec


def _write_requests(path: Path, rows: list[tuple[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("ticker", "quarter"))
        writer.writerows(rows)


def _cache(store: FileTranscriptStore, ticker: str, quarter: str) -> None:
    store.save(
        EarningsCallTranscript(
            provider="alpha_vantage",
            ticker=ticker,
            fiscal_quarter=quarter,
            turns=(
                TranscriptTurn(
                    speaker="CEO",
                    title="Chief Executive Officer",
                    text="Our earnings call was held on July 27, 2021.",
                ),
            ),
        )
    )


def test_progress_drafts_complete_case_and_leaves_incomplete_case_waiting(monkeypatch, tmp_path: Path) -> None:
    complete_requests = tmp_path / "complete.csv"
    incomplete_requests = tmp_path / "incomplete.csv"
    _write_requests(complete_requests, [("AAA", "2021Q2"), ("AAA", "2021Q1")])
    _write_requests(incomplete_requests, [("BBB", "2021Q2"), ("BBB", "2021Q1")])

    monkeypatch.setattr(
        validation_progress_cli,
        "STATIC_CASES",
        (
            ValidationCaseSpec(
                case_id="complete-case",
                requests=complete_requests,
                current_quarter="2021Q2",
                baseline_quarter="2021Q1",
                sector="Information Technology",
            ),
            ValidationCaseSpec(
                case_id="incomplete-case",
                requests=incomplete_requests,
                current_quarter="2021Q2",
                baseline_quarter="2021Q1",
                sector="Information Technology",
            ),
        ),
    )

    transcript_root = tmp_path / "transcripts"
    store = FileTranscriptStore(transcript_root)
    _cache(store, "AAA", "2021Q2")
    _cache(store, "AAA", "2021Q1")
    _cache(store, "BBB", "2021Q2")

    output = tmp_path / "progress.json"
    metadata_root = tmp_path / "metadata"
    missing_blind_requests = tmp_path / "missing-blind.csv"
    missing_blind_selection = tmp_path / "missing-selection.json"

    assert validation_progress_cli.main(
        [
            "--transcript-root", str(transcript_root),
            "--blind-requests", str(missing_blind_requests),
            "--blind-selection", str(missing_blind_selection),
            "--metadata-root", str(metadata_root),
            "--output", str(output),
        ]
    ) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["metadata_drafted_cases"] == 1
    assert payload["awaiting_transcript_cases"] == 1
    assert payload["cases"][0]["status"] == "metadata_drafted"
    assert payload["cases"][1]["status"] == "awaiting_transcripts"
    assert (metadata_root / "complete-case-current.csv").exists()
    assert (metadata_root / "complete-case-baseline.csv").exists()
    checklist = (metadata_root / "complete-case-checklist.csv").read_text(encoding="utf-8")
    assert "needs_verified_timestamp" in checklist
