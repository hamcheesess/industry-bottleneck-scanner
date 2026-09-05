from pathlib import Path

from industry_bottleneck_scanner.pipeline_fingerprint import (
    compute_experiment_input_fingerprint,
    missing_experiment_transcripts,
)
from industry_bottleneck_scanner.transcript_store import FileTranscriptStore
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


def _metadata(path: Path, quarter: str) -> None:
    path.write_text(f"ticker,quarter\nAAA,{quarter}\n", encoding="utf-8")


def _save(root: Path, quarter: str, text: str) -> None:
    FileTranscriptStore(root).save(
        EarningsCallTranscript(
            provider="fixture",
            ticker="AAA",
            fiscal_quarter=quarter,
            turns=(TranscriptTurn(speaker="CEO", title="CEO", text=text),),
        )
    )


def test_input_fingerprint_changes_when_cached_transcript_changes(tmp_path: Path) -> None:
    current = tmp_path / "current.csv"
    baseline = tmp_path / "baseline.csv"
    root = tmp_path / "transcripts"
    _metadata(current, "2026Q2")
    _metadata(baseline, "2026Q1")
    _save(root, "2026Q2", "Record backlog.")
    _save(root, "2026Q1", "Backlog was stable.")

    first = compute_experiment_input_fingerprint(
        current_metadata=current,
        baseline_metadata=baseline,
        provider="fixture",
        transcript_root=root,
        aggregation_level="industry",
        max_companies=50,
    )
    _save(root, "2026Q2", "Record backlog and constrained capacity.")
    second = compute_experiment_input_fingerprint(
        current_metadata=current,
        baseline_metadata=baseline,
        provider="fixture",
        transcript_root=root,
        aggregation_level="industry",
        max_companies=50,
    )

    assert first != second
    assert len(first) == 64
    assert len(second) == 64


def test_input_fingerprint_changes_when_result_affecting_runtime_config_changes(tmp_path: Path) -> None:
    current = tmp_path / "current.csv"
    baseline = tmp_path / "baseline.csv"
    root = tmp_path / "transcripts"
    _metadata(current, "2026Q2")
    _metadata(baseline, "2026Q1")
    _save(root, "2026Q2", "Record backlog.")
    _save(root, "2026Q1", "Backlog was stable.")

    industry = compute_experiment_input_fingerprint(
        current_metadata=current,
        baseline_metadata=baseline,
        provider="fixture",
        transcript_root=root,
        aggregation_level="industry",
        max_companies=50,
    )
    sector = compute_experiment_input_fingerprint(
        current_metadata=current,
        baseline_metadata=baseline,
        provider="fixture",
        transcript_root=root,
        aggregation_level="sector",
        max_companies=50,
    )
    limited = compute_experiment_input_fingerprint(
        current_metadata=current,
        baseline_metadata=baseline,
        provider="fixture",
        transcript_root=root,
        aggregation_level="industry",
        max_companies=5,
    )

    assert industry != sector
    assert industry != limited


def test_missing_experiment_transcripts_reports_exact_window_request(tmp_path: Path) -> None:
    current = tmp_path / "current.csv"
    baseline = tmp_path / "baseline.csv"
    root = tmp_path / "transcripts"
    _metadata(current, "2026Q2")
    _metadata(baseline, "2026Q1")
    _save(root, "2026Q2", "Record backlog.")

    assert missing_experiment_transcripts(
        current_metadata=current,
        baseline_metadata=baseline,
        provider="fixture",
        transcript_root=root,
    ) == ("baseline:AAA:2026Q1",)
