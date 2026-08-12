import csv
import json

from industry_bottleneck_scanner import cohort_cli


def test_cohort_cli_emits_paired_requests(tmp_path) -> None:
    candidates = tmp_path / "candidates.csv"
    candidates.write_text(
        "company_id,ticker,sector,industry,exchange\n"
        "issuer-a,AAA,Technology,Semiconductors,NASDAQ\n"
        "issuer-b,BBB,Industrials,Machinery,NYSE\n"
        "issuer-c,CCC,Healthcare,Medical Devices,NYSE\n"
        "issuer-d,DDD,Financials,Banks,NASDAQ\n",
        encoding="utf-8",
    )
    selection = tmp_path / "selection.json"
    requests = tmp_path / "requests.csv"

    assert cohort_cli.main(
        [
            "--candidates", str(candidates),
            "--target-size", "3",
            "--current-quarter", "2026Q2",
            "--baseline-quarter", "2026Q1",
            "--selection-output", str(selection),
            "--requests-output", str(requests),
        ]
    ) == 0

    payload = json.loads(selection.read_text(encoding="utf-8"))
    assert payload["diagnostics"]["selected_companies"] == 3
    assert payload["current_quarter"] == "2026Q2"
    assert payload["baseline_quarter"] == "2026Q1"

    with requests.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 6
    assert {row["quarter"] for row in rows} == {"2026Q2", "2026Q1"}
