from industry_bottleneck_scanner.iwv_proxy import candidates_to_csv, parse_iwv_holdings_csv


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
"CASH","USD CASH","Cash and/or Derivatives","Cash","5","0.1","5","5","1","United States","-","USD","1","USD","-"
"FOREIGN","FOREIGN PLC","Industrials","Equity","4","0.1","4","1","4","United Kingdom","LSE","USD","1","USD","-"
'''


def test_iwv_parser_marks_proxy_classification_and_filters_non_us_equity() -> None:
    snapshot = parse_iwv_holdings_csv(SAMPLE)
    assert snapshot.as_of.isoformat() == "2026-08-07"
    assert [item.ticker for item in snapshot.candidates] == ["AAA", "BBB"]
    assert snapshot.candidates[0].industry == "proxy-sector::Industrials"
    assert snapshot.candidates[1].exchange == "NASDAQ"


def test_iwv_candidates_emit_neutral_cohort_contract() -> None:
    snapshot = parse_iwv_holdings_csv(SAMPLE)
    text = candidates_to_csv(snapshot)
    assert text.startswith("company_id,ticker,sector,industry,exchange\n")
    assert "ticker-AAA,AAA,Industrials,proxy-sector::Industrials,NYSE" in text
