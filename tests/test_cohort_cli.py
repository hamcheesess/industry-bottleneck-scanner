import csv
import json

from industry_bottleneck_scanner import cohort_cli


def test_cohort_cli_emits_trigger_reachable_paired_requests(tmp_path) -> None:
    candidates = tmp_path / "candidates.csv"
    candidates.write_text(
        "company_id,ticker,sector,industry,exchange\n"
        "issuer-a1,AAA1,Technology,Semiconductors,NASDAQ\n"
        "issuer-a2,AAA2,Technology,Semiconductors,NASDAQ\n"
        "issuer-a3,AAA3,Technology,Semiconductors,NASDAQ\n"
        "issuer-a4,AAA4,Technology,Semiconductors,NASDAQ\n"
        "issuer-b1,BBB1,Industrials,Machinery,NYSE\n"
        "issuer-b2,BBB2,Industrials,Machinery,NYSE\n"
        "issuer-b3,BBB3,Industrials,Machinery,NYSE\n"
        "issuer-b4,BBB4,Industrials,Machinery,NYSE\n",
        encoding="utf-8",
    )
    selection = tmp_path / "selection.json"
    requests = tmp_path / "requests.csv"

    assert cohort_cli.main(
        [
            "--candidates", str(candidates),
            "--as-of", "2026-06-29",
            "--source", "dated broad-US validation snapshot",
            "--industry-count", "2",
            "--companies-per-industry", "4",
            "--current-quarter", "2026Q2",
            "--baseline-quarter", "2026Q1",
            "--selection-output", str(selection),
            "--requests-output", str(requests),
        ]
    ) == 0

    payload = json.loads(selection.read_text(encoding="utf-8"))
    assert payload["diagnostics"]["selected_companies"] == 8
    assert payload["diagnostics"]["industries_selected"] == 2
    assert payload["diagnostics"]["companies_per_industry"] == 4
    assert payload["sampling_contract"]["selection_uses_scanner_outcomes"] is False
    assert payload["current_quarter"] == "2026Q2"
    assert payload["baseline_quarter"] == "2026Q1"
    assert payload["universe_provenance"]["as_of"] == "2026-06-29"

    with requests.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 16
    assert {row["quarter"] for row in rows} == {"2026Q2", "2026Q1"}
