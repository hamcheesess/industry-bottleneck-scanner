import json
from pathlib import Path

from industry_bottleneck_scanner import batch_cli
from industry_bottleneck_scanner.pipeline_fingerprint import RESULT_SCHEMA_VERSION
from industry_bottleneck_scanner.transcript_store import FileTranscriptStore
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


def _write_manifest(path: Path, quarter: str, published_at: str) -> None:
    path.write_text(
        "ticker,company_id,quarter,published_at,industry\n"
        f"POWL,issuer-powl,{quarter},{published_at},Electrical Equipment\n",
        encoding="utf-8",
    )


def _save(store: FileTranscriptStore, quarter: str) -> None:
    store.save(
        EarningsCallTranscript(
            provider="fixture",
            ticker="POWL",
            fiscal_quarter=quarter,
            turns=(
                TranscriptTurn(
                    speaker="CEO",
                    title="CEO",
                    text="Backlog reached a record level and capacity remains constrained.",
                ),
            ),
        )
    )


def test_batch_cli_writes_cache_only_experiment_summary(tmp_path) -> None:
    current = tmp_path / "current.csv"
    baseline = tmp_path / "baseline.csv"
    _write_manifest(current, "2026Q2", "2026-05-06T20:00:00+00:00")
    _write_manifest(baseline, "2026Q1", "2026-02-06T20:00:00+00:00")

    transcript_root = tmp_path / "transcripts"
    store = FileTranscriptStore(transcript_root)
    _save(store, "2026Q2")
    _save(store, "2026Q1")
    output = tmp_path / "result.json"
    artifact_root = tmp_path / "artifacts"

    assert (
        batch_cli.main(
            [
                "--current",
                str(current),
                "--baseline",
                str(baseline),
                "--provider",
                "fixture",
                "--transcript-root",
                str(transcript_root),
                "--review-queue",
                str(tmp_path / "review.json"),
                "--output",
                str(output),
                "--artifact-root",
                str(artifact_root),
            ]
        )
        == 0
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["provider"] == "fixture"
    provenance = payload["result_provenance"]
    assert provenance["schema_version"] == RESULT_SCHEMA_VERSION
    assert len(provenance["pipeline_fingerprint"]) == 64
    assert len(provenance["input_fingerprint"]) == 64
    assert provenance["current_metadata"] == str(current)
    assert provenance["baseline_metadata"] == str(baseline)
    assert payload["current"]["signal_count"] >= 2
    assert payload["current"]["missing_transcripts"] == 0
    assert payload["baseline"]["missing_transcripts"] == 0
    assert payload["acceleration"][0]["bucket"] == "Electrical Equipment"
    assert "discovery_score" in payload["acceleration"][0]
    assert payload["current"]["diagnostics"]["distinct_companies"] == 1
    assert payload["current"]["diagnostics"]["top_company_share"] == 1.0
    assert payload["phase1_viability"]["decision"] == "expand_neutral_cohort"
    assert isinstance(payload["taxonomy_candidates"], list)
    assert (artifact_root / "current_signals.jsonl").exists()
    assert (artifact_root / "baseline_signals.jsonl").exists()
    assert (artifact_root / "handoff_preview.json").exists()
    assert (artifact_root / "taxonomy_candidates.json").exists()
    assert (artifact_root / "phase1_viability.json").exists()
    assert payload["artifacts"]["current_signals_jsonl"] == str(
        artifact_root / "current_signals.jsonl"
    )
