import csv
import json
from pathlib import Path

from industry_bottleneck_scanner import validation_advance_cli
from industry_bottleneck_scanner.validation_advance_cli import VerifiedCase


def _write_draft(path: Path, quarter: str) -> None:
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
                "published_date_candidate",
                "published_date_evidence",
                "metadata_status",
            )
        )
        writer.writerow(("AAA", "ticker-AAA", quarter, "", "Technology", "", "", "", "", "", "needs_verified_timestamp"))


def test_advance_finalizes_exact_draft_rows_and_invokes_runner(monkeypatch, tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    _write_draft(metadata_root / "case-a-current.csv", "2021Q2")
    _write_draft(metadata_root / "case-a-baseline.csv", "2021Q1")

    verified = tmp_path / "verified.csv"
    verified.write_text(
        "ticker,quarter,published_at,published_at_source_url\n"
        "AAA,2021Q2,2021-07-27T14:00:00-07:00,https://example.com/q2\n"
        "AAA,2021Q1,2021-04-27T14:00:00-07:00,https://example.com/q1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        validation_advance_cli,
        "VERIFIED_CASES",
        (VerifiedCase(case_id="case-a", verified=verified),),
    )

    run_output = tmp_path / "run-status.json"

    def fake_run(argv: list[str]) -> int:
        output = Path(argv[argv.index("--output") + 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "status": "partial",
                    "completed_cases": 1,
                    "awaiting_verified_metadata_cases": 2,
                }
            ),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(validation_advance_cli, "run_main", fake_run)
    output = tmp_path / "advance.json"

    assert validation_advance_cli.main(
        [
            "--metadata-root", str(metadata_root),
            "--subset-root", str(tmp_path / "subsets"),
            "--run-output", str(run_output),
            "--output", str(output),
        ]
    ) == 0

    with (metadata_root / "case-a-current.csv").open("r", encoding="utf-8", newline="") as handle:
        current = next(csv.DictReader(handle))
    with (metadata_root / "case-a-baseline.csv").open("r", encoding="utf-8", newline="") as handle:
        baseline = next(csv.DictReader(handle))

    assert current["published_at"] == "2021-07-27T14:00:00-07:00"
    assert baseline["published_at"] == "2021-04-27T14:00:00-07:00"
    assert current["metadata_status"] == "verified"
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["finalized_cases"] == ["case-a"]
    assert payload["run_status"]["completed_cases"] == 1
