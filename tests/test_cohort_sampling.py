from industry_bottleneck_scanner.cohort_sampling import (
    CohortCandidate,
    load_cohort_candidates_csv,
    select_neutral_cohort,
)


def _candidate(index: int, sector: str, industry: str) -> CohortCandidate:
    return CohortCandidate(
        company_id=f"issuer-{index}",
        ticker=f"T{index}",
        sector=sector,
        industry=industry,
        exchange="NASDAQ" if index % 2 else "NYSE",
    )


def test_loader_requires_classification_and_identity() -> None:
    rows = load_cohort_candidates_csv(
        "company_id,ticker,sector,industry,exchange\n"
        "issuer-a,AAA,Technology,Semiconductors,NASDAQ\n"
    )
    assert rows[0].ticker == "AAA"
    assert rows[0].sector == "Technology"


def test_selection_is_reproducible_and_cross_sector() -> None:
    candidates = (
        _candidate(1, "Technology", "Semiconductors"),
        _candidate(2, "Technology", "Software"),
        _candidate(3, "Industrials", "Electrical Equipment"),
        _candidate(4, "Industrials", "Machinery"),
        _candidate(5, "Healthcare", "Biotechnology"),
        _candidate(6, "Healthcare", "Medical Devices"),
        _candidate(7, "Energy", "Oil & Gas"),
        _candidate(8, "Financials", "Banks"),
    )

    first = select_neutral_cohort(candidates, target_size=6, max_per_industry=1, seed="fixed")
    second = select_neutral_cohort(tuple(reversed(candidates)), target_size=6, max_per_industry=1, seed="fixed")

    assert first.companies == second.companies
    assert first.diagnostics.selected_companies == 6
    assert first.diagnostics.sectors_selected >= 4
    assert len({item.industry for item in first.companies}) == 6


def test_industry_cap_prevents_one_industry_from_dominating() -> None:
    candidates = tuple(
        _candidate(index, "Technology", "Semiconductors")
        for index in range(1, 7)
    ) + (
        _candidate(7, "Industrials", "Machinery"),
        _candidate(8, "Healthcare", "Medical Devices"),
    )

    selection = select_neutral_cohort(candidates, target_size=6, max_per_industry=2)
    semiconductor_count = sum(item.industry == "Semiconductors" for item in selection.companies)

    assert semiconductor_count <= 2
