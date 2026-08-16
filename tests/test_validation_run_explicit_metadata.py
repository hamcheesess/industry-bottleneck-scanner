import csv
from pathlib import Path

from industry_bottleneck_scanner import validation_run_cli


def _write_metadata(path: Path, quarter: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
        writer.writerow(
            (
                "AAA",
                "issuer-a",
                quarter,
                "2026-07-31T15:00:00+00:00",
                "Industrials",
                "Electrical Equipment",
                "Power",
                "https://example.test/event",
            )
        )


def test_runner_uses_explicit_metadata_paths_from_frozen_manifest(monkeypatch, tmp_path: Path) -> None:
    current = tmp_path / "experiments" / "current.csv"
    baseline = tmp_path / "experiments" / "baseline.csv"
    _write_metadata(current, "2026Q2")
    _write_metadata(baseline, "2026Q1")
    cases = tmp_path / "cases.csv"
    cases.write_text(
        "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources,notes,current_metadata_path,baseline_metadata_path\n"
        f"power,positive,{tmp_path / 'result.json'},industry,Electrical Equipment,backlog_strength,https://example.test/source,pilot,{current},{baseline}\n",
        encoding="utf-8",
    )
    calls: list[list[str]] = []
    monkeypatch.setattr(validation_run_cli, "batch_main", lambda argv: calls.append(list(argv)) or 0)

    assert validation_run_cli.main(
        ["--cases", str(cases), "--metadata-root", str(tmp_path / "unused")]
    ) == 0
    assert calls
    assert calls[0][calls[0].index("--current") + 1] == str(current)
    assert calls[0][calls[0].index("--baseline") + 1] == str(baseline)
