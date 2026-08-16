import csv
import json
from pathlib import Path

from industry_bottleneck_scanner import validation_run_cli


def _write_metadata(path: Path, *, published_at: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            (
                "ticker",
                "company_id",
                "quarter",
                "published_at",
                "sector",
                "industry",
                "subindustry",
                "published_at_source_url",
            )
        )
        writer.writerow(("AAA", "issuer-a", "2021Q2", published_at, "Technology", "Semiconductors", "", "https://example.com/event"))


def test_runner_skips_case_until_verified_timestamps(monkeypatch, tmp_path: Path) -> None:
    cases = tmp_path / "cases.csv"
    cases.write_text(
        "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources,notes\n"
        "case-a,positive,result.json,sector,Technology,,,\n",
        encoding="utf-8",
    )
    metadata_root = tmp_path / "metadata"
    metadata_root.mkdir()
    _write_metadata(metadata_root / "case-a-current.csv", published_at="")
    _write_metadata(metadata_root / "case-a-baseline.csv", published_at="")
    output = tmp_path / "run-status.json"

    def fail_batch(argv):  # pragma: no cover - should never be called
        raise AssertionError("batch runner must not run with unverified timestamps")

    monkeypatch.setattr(validation_run_cli, "batch_main", fail_batch)
    assert validation_run_cli.main([
        "--cases", str(cases),
        "--metadata-root", str(metadata_root),
        "--output", str(output),
    ]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "partial"
    assert payload["completed_cases"] == 0
    assert payload["awaiting_verified_metadata_cases"] == 1
    assert payload["awaiting_transcript_cases"] == 0
    assert payload["cases"][0]["status"] == "awaiting_verified_metadata"


def test_runner_skips_verified_case_until_all_transcripts_are_cached(monkeypatch, tmp_path: Path) -> None:
    cases = tmp_path / "cases.csv"
    cases.write_text(
        "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources,notes\n"
        "case-a,positive,result.json,sector,Technology,,,\n",
        encoding="utf-8",
    )
    metadata_root = tmp_path / "metadata"
    metadata_root.mkdir()
    _write_metadata(metadata_root / "case-a-current.csv", published_at="2021-07-27T16:00:00+00:00")
    _write_metadata(metadata_root / "case-a-baseline.csv", published_at="2021-04-27T16:00:00+00:00")
    output = tmp_path / "run-status.json"

    monkeypatch.setattr(
        validation_run_cli,
        "missing_experiment_transcripts",
        lambda **kwargs: ("baseline:AAA:2021Q2",),
    )
    monkeypatch.setattr(
        validation_run_cli,
        "batch_main",
        lambda argv: (_ for _ in ()).throw(AssertionError("batch runner must not run with missing cache")),
    )

    assert validation_run_cli.main([
        "--cases", str(cases),
        "--metadata-root", str(metadata_root),
        "--output", str(output),
    ]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["completed_cases"] == 0
    assert payload["awaiting_transcript_cases"] == 1
    assert payload["cases"][0]["status"] == "awaiting_transcripts"
    assert payload["cases"][0]["missing_transcripts"] == ["baseline:AAA:2021Q2"]


def test_runner_executes_ready_case_with_frozen_aggregation(monkeypatch, tmp_path: Path) -> None:
    cases = tmp_path / "cases.csv"
    result = tmp_path / "result.json"
    cases.write_text(
        "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources,notes\n"
        f"case-a,positive,{result},sector,Technology,,,\n",
        encoding="utf-8",
    )
    metadata_root = tmp_path / "metadata"
    metadata_root.mkdir()
    _write_metadata(metadata_root / "case-a-current.csv", published_at="2021-07-27T16:00:00+00:00")
    _write_metadata(metadata_root / "case-a-baseline.csv", published_at="2021-04-27T16:00:00+00:00")
    output = tmp_path / "run-status.json"
    calls: list[list[str]] = []

    monkeypatch.setattr(validation_run_cli, "missing_experiment_transcripts", lambda **kwargs: ())

    def fake_batch(argv):
        calls.append(list(argv))
        return 0

    monkeypatch.setattr(validation_run_cli, "batch_main", fake_batch)
    assert validation_run_cli.main([
        "--cases", str(cases),
        "--metadata-root", str(metadata_root),
        "--output", str(output),
    ]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "complete"
    assert payload["completed_cases"] == 1
    assert payload["awaiting_transcript_cases"] == 0
    assert "--aggregation-level" in calls[0]
    assert calls[0][calls[0].index("--aggregation-level") + 1] == "sector"
    assert calls[0][calls[0].index("--max-companies") + 1] == "50"
