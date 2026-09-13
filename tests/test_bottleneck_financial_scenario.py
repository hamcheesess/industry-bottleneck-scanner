from __future__ import annotations

import json

import pytest

from industry_bottleneck_scanner.bottleneck_financial_scenario import (
    build_bottleneck_financial_scenario,
    write_bottleneck_financial_scenario,
)
from industry_bottleneck_scanner.bottleneck_financial_scenario_cli import main


def evidence() -> list[dict[str, object]]:
    return [
        {
            "evidence_id": "issuer",
            "source_id": "sec:test",
            "source_class": "issuer_primary",
            "observed_at": "2026-08-28T00:00:00+00:00",
            "title": "회사 생산능력과 기준 재무",
        },
        {
            "evidence_id": "government",
            "source_id": "gov:test",
            "source_class": "government_regulator",
            "observed_at": "2026-08-20T00:00:00+00:00",
            "title": "정부 수요 자료",
        },
        {
            "evidence_id": "industry",
            "source_id": "industry:test",
            "source_class": "industry_technical",
            "observed_at": "2026-08-21T00:00:00+00:00",
            "title": "산업 공급능력 자료",
        },
        {
            "evidence_id": "physical",
            "source_id": "physical:test",
            "source_class": "physical_market_data",
            "observed_at": "2026-08-25T00:00:00+00:00",
            "title": "실물 주문과 납기 자료",
        },
        {
            "evidence_id": "market",
            "source_id": "market:test",
            "source_class": "market_expectations",
            "observed_at": "2026-08-30T00:00:00+00:00",
            "title": "시장 가격과 추정치",
        },
    ]


def case(scenario: str, horizon: int) -> dict[str, object]:
    settings = {
        "downside": {
            "demand": 60.0,
            "supply": 35.0,
            "capture": 0.20,
            "capacity": 8.0,
            "price": 8.0,
            "cost": 6.0,
            "fixed": 0.0,
            "working_capital": 1.0,
            "capex": 1.0,
            "multiple": 9.0,
        },
        "base": {
            "demand": 140.0,
            "supply": 40.0,
            "capture": 0.20,
            "capacity": 20.0,
            "price": 10.0,
            "cost": 5.0,
            "fixed": 0.0,
            "working_capital": 10.0,
            "capex": 5.0,
            "multiple": 10.0,
        },
        "upside": {
            "demand": 200.0,
            "supply": 35.0,
            "capture": 0.25,
            "capacity": 30.0,
            "price": 11.0,
            "cost": 5.0,
            "fixed": 5.0,
            "working_capital": 15.0,
            "capex": 8.0,
            "multiple": 11.0,
        },
    }[scenario]
    scale = {6: 0.5, 12: 1.0, 18: 1.2}[horizon]
    return {
        "scenario_id": scenario,
        "horizon_months": horizon,
        "industry_incremental_demand_units": settings["demand"] * scale,
        "industry_incremental_supply_units": settings["supply"] * scale,
        "company_capture_share": settings["capture"],
        "company_available_incremental_capacity_units": settings["capacity"] * scale,
        "realized_price_per_unit": settings["price"],
        "variable_cost_per_unit": settings["cost"],
        "incremental_fixed_cost": settings["fixed"] * scale,
        "incremental_working_capital": settings["working_capital"] * scale,
        "incremental_capex": settings["capex"] * scale,
        "tax_rate": 0.20,
        "valuation_multiple": settings["multiple"],
        "assumption_posture": "analyst_assumption",
        "evidence_ids": ["government", "industry", "physical"],
        "confirmers_ko": [
            "다음 두 분기 신규 수주가 기준 시나리오의 물량을 확인합니다.",
            "판매가격과 증분 이익률이 가정 범위 이상으로 유지됩니다.",
        ],
        "falsifiers_ko": [
            "공급 증설이 예상보다 빨라 고객 대기기간이 정상화됩니다.",
            "수주 증가가 매출과 현금흐름으로 전환되지 않습니다.",
        ],
    }


def payload() -> dict[str, object]:
    return {
        "schema_version": "bottleneck-financial-scenario-input-v1",
        "scenario_run_id": "scenario-test-1",
        "candidate_id": "candidate-test-1",
        "node_id": "large-power-transformers",
        "as_of": "2026-08-31T12:00:00+00:00",
        "currency": "USD_millions",
        "volume_unit": "normalized_transformer_units",
        "period_basis": "forward_annualized_at_horizon",
        "evidence": evidence(),
        "company": {
            "ticker": "TEST",
            "company_name": "가상 시험 기업",
            "current_price": 100.0,
            "market_data_as_of": "2026-08-31T00:00:00+00:00",
            "shares_diluted": 10.0,
            "net_debt": 100.0,
            "baseline_forward_revenue": 1000.0,
            "baseline_forward_operating_income": 100.0,
            "baseline_forward_fcf": 80.0,
            "evidence_ids": ["issuer", "market"],
        },
        "market_expectations": [
            {
                "horizon_months": horizon,
                "as_of": "2026-08-30T00:00:00+00:00",
                "forward_revenue": 1050.0,
                "forward_operating_income": 110.0,
                "forward_fcf": 90.0,
                "valuation_multiple": 10.0,
                "evidence_ids": ["market"],
            }
            for horizon in (6, 12, 18)
        ],
        "cases": [
            case(scenario, horizon)
            for horizon in (6, 12, 18)
            for scenario in ("downside", "base", "upside")
        ],
        "catalysts": [
            {
                "catalyst_id": "earnings-1",
                "title_ko": "다음 분기 수주와 매출 전환 확인",
                "event_at": "2026-11-01T12:00:00+00:00",
                "date_status": "inferred",
                "evidence_ids": ["issuer"],
            },
            {
                "catalyst_id": "earnings-2",
                "title_ko": "두 번째 실적 발표에서 이익률 확인",
                "event_at": "2027-02-01T12:00:00+00:00",
                "date_status": "inferred",
                "evidence_ids": ["issuer"],
            },
        ],
    }


def scenario_row(output: dict[str, object], scenario: str, horizon: int) -> dict[str, object]:
    return next(
        row
        for row in output["scenario_rows"]
        if row["scenario_id"] == scenario and row["horizon_months"] == horizon
    )


def test_builds_strict_3x3_financial_bridge_and_advances_good_skew() -> None:
    output = build_bottleneck_financial_scenario(payload())

    assert output["schema_version"] == "bottleneck-financial-scenario-output-v1"
    assert output["strict_as_of"] is True
    assert output["security_level_recommendation"] is False
    assert len(output["scenario_rows"]) == 9
    base = scenario_row(output, "base", 12)
    assert base["industry_shortage_units"] == 100.0
    assert base["company_captured_volume_units"] == 20.0
    assert base["incremental_revenue"] == 200.0
    assert base["incremental_operating_income"] == 100.0
    assert base["incremental_fcf"] == 65.0
    assert base["projected_forward_operating_income"] == 200.0
    assert base["operating_income_gap_vs_market"] == 90.0
    assert base["fundamental_only_value_per_share"] == 190.0
    assert base["expected_return"] == 0.9
    assert base["upside_driver"] == "fundamentals"
    assert output["readiness"]["status"] == "senior_review_ready"
    assert output["investment_research_decision"]["status"] == "advance_to_deeper_work"
    assert "증분 매출은 200.00 USD_millions" in output["investor_summary_ko"][
        "bottleneck_to_revenue"
    ]
    assert "시장 기대보다 90.00 USD_millions" in output["investor_summary_ko"][
        "market_expectations_gap"
    ]


def test_capacity_caps_company_volume_even_when_shortage_is_larger() -> None:
    value = payload()
    base = next(
        row
        for row in value["cases"]
        if row["scenario_id"] == "base" and row["horizon_months"] == 12
    )
    base["company_available_incremental_capacity_units"] = 7.0

    output = build_bottleneck_financial_scenario(value)
    row = scenario_row(output, "base", 12)
    assert row["company_addressable_volume_units"] == 20.0
    assert row["company_captured_volume_units"] == 7.0
    assert row["incremental_revenue"] == 70.0


def test_post_as_of_evidence_is_rejected() -> None:
    value = payload()
    value["evidence"][0]["observed_at"] = "2026-09-01T00:00:00+00:00"

    with pytest.raises(ValueError, match="post-as-of evidence"):
        build_bottleneck_financial_scenario(value)


def test_exact_6_12_18_downside_base_upside_grid_is_required() -> None:
    value = payload()
    value["cases"].pop()

    with pytest.raises(ValueError, match="3x3 scenario grid"):
        build_bottleneck_financial_scenario(value)


def test_each_case_requires_two_source_classes() -> None:
    value = payload()
    value["cases"][0]["evidence_ids"] = ["government"]

    with pytest.raises(ValueError, match="requires two source classes"):
        build_bottleneck_financial_scenario(value)


def test_inverted_scenario_labels_are_rejected() -> None:
    value = payload()
    downside = next(
        row
        for row in value["cases"]
        if row["scenario_id"] == "downside" and row["horizon_months"] == 12
    )
    downside["industry_incremental_demand_units"] = 300.0

    with pytest.raises(ValueError, match="scenario ordering is inverted"):
        build_bottleneck_financial_scenario(value)


def test_stale_price_data_caps_readiness_and_waits_for_proof() -> None:
    value = payload()
    value["company"]["market_data_as_of"] = "2026-08-01T00:00:00+00:00"

    output = build_bottleneck_financial_scenario(value)
    assert output["readiness"]["status"] == "screen_grade"
    assert output["investment_research_decision"]["status"] == "wait_for_proof"
    assert "source_or_market_data_not_review_ready" in output[
        "investment_research_decision"
    ]["gate_reasons"]


def test_no_positive_market_gap_rejects_candidate() -> None:
    value = payload()
    for expectation in value["market_expectations"]:
        expectation["forward_operating_income"] = 250.0
        expectation["forward_fcf"] = 200.0

    output = build_bottleneck_financial_scenario(value)
    assert output["investment_research_decision"]["status"] == "reject_no_expectation_gap"
    assert output["investment_research_decision"]["first_rejection"] == (
        "no_positive_12m_expectation_gap"
    )


def test_multiple_only_upside_is_labeled_not_hidden() -> None:
    value = payload()
    downside = next(
        row
        for row in value["cases"]
        if row["scenario_id"] == "downside" and row["horizon_months"] == 12
    )
    downside["industry_incremental_demand_units"] = 20.0
    base = next(
        row
        for row in value["cases"]
        if row["scenario_id"] == "base" and row["horizon_months"] == 12
    )
    base["industry_incremental_demand_units"] = 40.0
    base["industry_incremental_supply_units"] = 40.0
    base["valuation_multiple"] = 15.0

    output = build_bottleneck_financial_scenario(value)
    row = scenario_row(output, "base", 12)
    assert row["incremental_operating_income"] == 0.0
    assert row["upside_driver"] == "multiple_expansion_only"


def test_fewer_than_two_catalysts_cannot_advance() -> None:
    value = payload()
    value["catalysts"] = value["catalysts"][:1]

    output = build_bottleneck_financial_scenario(value)
    assert output["investment_research_decision"]["status"] == "wait_for_proof"
    assert "insufficient_18m_catalysts" in output["investment_research_decision"][
        "gate_reasons"
    ]


def test_cli_writes_json_and_compact_csv(tmp_path, monkeypatch, capsys) -> None:
    input_path = tmp_path / "scenario.json"
    input_path.write_text(json.dumps(payload(), ensure_ascii=False), encoding="utf-8")
    output_dir = tmp_path / "output"
    monkeypatch.setattr(
        "sys.argv",
        [
            "ibs-bottleneck-financial-scenario",
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
        ],
    )

    main()

    output = json.loads((output_dir / "bottleneck_financial_scenario.json").read_text())
    csv_text = (output_dir / "bottleneck_financial_scenario.csv").read_text()
    assert output["scenario_sha256"]
    assert len(csv_text.splitlines()) == 10
    assert "decision=advance_to_deeper_work" in capsys.readouterr().out


def test_writer_creates_only_deterministic_support_artifacts(tmp_path) -> None:
    output = build_bottleneck_financial_scenario(payload())
    write_bottleneck_financial_scenario(tmp_path, output)

    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "bottleneck_financial_scenario.csv",
        "bottleneck_financial_scenario.json",
    ]
