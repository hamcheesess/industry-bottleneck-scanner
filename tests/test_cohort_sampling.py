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
    candidates = tuple(
        _candidate(index, "Technology", "Semiconductors")
        for index in range(1, 5)
    ) + tuple(
        _candidate(index, "Industrials", "Electrical Equipment")
        for index in range(5, 9)
    ) + tuple(
        _candidate(index, "Healthcare", "Medical Devices")
        for index in range(9, 13)
    )

    first = select_neutral_cohort(
        candidates,
        industry_count=3,
        companies_per_industry=4,
        seed="fixed",
    )
    second = select_neutral_cohort(
        tuple(reversed(candidates)),
        industry_count=3,
        companies_per_industry=4,
        seed="fixed",
    )

    assert first.companies == second.companies
    assert first.diagnostics.selected_companies == 12
    assert first.diagnostics.sectors_selected == 3
    assert first.diagnostics.industries_selected == 3
    assert first.diagnostics.companies_per_industry == 4


def test_sampler_excludes_industries_below_trigger_reachable_breadth() -> None:
    candidates = tuple(
        _candidate(index, "Technology", "Semiconductors")
        for index in range(1, 5)
    ) + tuple(
        _candidate(index, "Industrials", "Machinery")
        for index in range(5, 7)
    )

    selection = select_neutral_cohort(
        candidates,
        industry_count=2,
        companies_per_industry=4,
    )

    assert {item.industry for item in selection.companies} == {"Semiconductors"}
    assert len(selection.companies) == 4
