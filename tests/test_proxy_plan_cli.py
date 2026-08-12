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
"AAA1","ALPHA 1","Industrials","Equity","100","1","100","1","100","United States","NYSE","USD","1","USD","-"
"AAA2","ALPHA 2","Industrials","Equity","99","1","99","1","99","United States","NYSE","USD","1","USD","-"
"AAA3","ALPHA 3","Industrials","Equity","98","1","98","1","98","United States","NYSE","USD","1","USD","-"
"BBB1","BETA 1","Information Technology","Equity","90","1","90","1","90","United States","NASDAQ","USD","1","USD","-"
"BBB2","BETA 2","Information Technology","Equity","89","1","89","1","89","United States","NASDAQ","USD","1","USD","-"
"BBB3","BETA 3","Information Technology","Equity","88","1","88","1","88","United States","NASDAQ","USD","1","USD","-"
'''


def test_proxy_plan_emits_trigger_reachable_selection_and_paired_requests(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(proxy_plan_cli, "_download", lambda url: SAMPLE)
    selection = tmp_path / "selection.json"
    requests = tmp_path / "requests.csv"

    code = proxy_plan_cli.main(
        [
            "--industry-count", "2",
            "--companies-per-industry", "3",
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
    assert payload["sampling_contract"]["selection_uses_scanner_outcomes"] is False
    assert payload["diagnostics"]["industries_selected"] == 2
    assert payload["diagnostics"]["companies_per_industry"] == 3
    assert len(payload["companies"]) == 6

    rows = list(csv.DictReader(requests.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 12
    by_ticker: dict[str, set[str]] = {}
    for row in rows:
        by_ticker.setdefault(row["ticker"], set()).add(row["quarter"])
    assert all(quarters == {"2026Q1", "2026Q2"} for quarters in by_ticker.values())
