import csv
import json
from pathlib import Path

from industry_bottleneck_scanner import proxy_plan_cli


SAMPLE = '''iShares Russell 3000 ETF
Fund Holdings as of,"Aug 07, 2026"
Inception Date,"May 22, 2000"
Shares Outstanding,"46,250,000.00"
Stock,"-"
Bond,"-"
Cash,"-"
Other,"-"
Ticker,Name,Sector,Asset Class,Market Value,Weight (%),Notional Value,Quantity,Price,Location,Exchange,Currency,FX Rate,Market Currency,Accrual Date
"AAA","ALPHA INC","Industrials","Equity","100","1","100","1","100","United States","NYSE","USD","1","USD","-"
"BBB","BETA INC","Information Technology","Equity","90","1","90","1","90","United States","NASDAQ","USD","1","USD","-"
"CCC","GAMMA INC","Health Care","Equity","80","1","80","1","80","United States","NYSE","USD","1","USD","-"
"DDD","DELTA INC","Financials","Equity","70","1","70","1","70","United States","NYSE","USD","1","USD","-"
'''


def test_proxy_plan_emits_reproducible_selection_and_paired_requests(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(proxy_plan_cli, "_download", lambda url: SAMPLE)
    selection = tmp_path / "selection.json"
    requests = tmp_path / "requests.csv"

    code = proxy_plan_cli.main(
        [
            "--target-size", "3",
            "--max-per-sector", "1",
            "--seed", "test-seed",
            "--selection-output", str(selection),
            "--requests-output", str(requests),
        ]
    )

    assert code == 0
    payload = json.loads(selection.read_text(encoding="utf-8"))
    assert payload["universe_provenance"]["canonical_russell_3000"] is False
    assert payload["universe_provenance"]["purpose"] == "phase1_validation_only"
    assert payload["universe_provenance"]["as_of"] == "2026-08-07"
    assert len(payload["companies"]) == 3

    rows = list(csv.DictReader(requests.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 6
    by_ticker: dict[str, set[str]] = {}
    for row in rows:
        by_ticker.setdefault(row["ticker"], set()).add(row["quarter"])
    assert all(quarters == {"2026Q1", "2026Q2"} for quarters in by_ticker.values())
