import csv
from pathlib import Path

import pytest

from industry_bottleneck_scanner import validation_metadata_finalize_cli


def _write_draft(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("ticker", "company_id", "quarter", "published_at", "sector", "industry", "subindustry", "published_at_source_url", "metadata_status"))
        writer.writerow(("AAA", "issuer-a", "2021Q2", "", "Technology", "", "", "", "needs_verified_timestamp"))


def test_finalize_requires_timezone_and_source_url(tmp_path: Path) -> None:
    draft = tmp_path / "draft.csv"
    verified = tmp_path / "verified.csv"
    output = tmp_path / "final.csv"
    _write_draft(draft)
    verified.write_text(
        "ticker,quarter,published_at,published_at_source_url\n"
        "AAA,2021Q2,2021-07-27T16:00:00,https://example.com/event\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="timezone offset"):
        validation_metadata_finalize_cli.main([
            "--draft", str(draft),
            "--verified", str(verified),
            "--output", str(output),
        ])


def test_finalize_applies_exact_pair_only(tmp_path: Path) -> None:
    draft = tmp_path / "draft.csv"
    verified = tmp_path / "verified.csv"
    output = tmp_path / "final.csv"
    _write_draft(draft)
    verified.write_text(
        "ticker,quarter,published_at,published_at_source_url\n"
        "AAA,2021Q2,2021-07-27T16:00:00+00:00,https://example.com/event\n",
        encoding="utf-8",
    )
    assert validation_metadata_finalize_cli.main([
        "--draft", str(draft),
        "--verified", str(verified),
        "--output", str(output),
    ]) == 0

    with output.open("r", encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["published_at"] == "2021-07-27T16:00:00+00:00"
    assert row["published_at_source_url"] == "https://example.com/event"
    assert row["metadata_status"] == "verified"
