from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path


FINANCIAL_SCENARIO_INPUT_SCHEMA = "bottleneck-financial-scenario-input-v1"
FINANCIAL_SCENARIO_OUTPUT_SCHEMA = "bottleneck-financial-scenario-output-v1"

SCENARIOS = ("downside", "base", "upside")
HORIZONS = (6, 12, 18)
SOURCE_POSTURES = {"reported", "source_derived", "analyst_assumption"}
SOURCE_CLASSES = {
    "issuer_primary",
    "customer_supplier_competitor",
    "government_regulator",
    "industry_technical",
    "market_expectations",
    "physical_market_data",
}

BASE_RETURN_HURDLE = 0.20
MAX_DOWNSIDE = -0.15
MIN_REWARD_TO_DOWNSIDE = 1.50


def _required_text(payload: dict[str, object], key: str, *, minimum: int = 1) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise ValueError(f"{key} must be text with at least {minimum} characters")
    return value.strip()


def _aware_datetime(value: object, name: str) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return parsed


def _number(
    value: object,
    name: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    if maximum is not None and result > maximum:
        raise ValueError(f"{name} must not exceed {maximum}")
    return result


def _integer(value: object, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer of at least {minimum}")
    return value


def _string_list(value: object, name: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{name} must be a list of non-empty strings")
    result = [item.strip() for item in value]
    if not allow_empty and not result:
        raise ValueError(f"{name} must not be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} must contain unique values")
    return result


def _canonical_sha256(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _percentage_gap(actual: float, expected: float) -> float | None:
    if expected == 0:
        return None
    return round((actual - expected) / abs(expected), 6)


def _evidence_index(raw: object, *, as_of: datetime) -> dict[str, dict[str, object]]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("evidence must be a non-empty list")
    result: dict[str, dict[str, object]] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"evidence[{index}] must be an object")
        evidence_id = _required_text(item, "evidence_id")
        source_id = _required_text(item, "source_id")
        source_class = _required_text(item, "source_class")
        if source_class not in SOURCE_CLASSES:
            raise ValueError(f"evidence {evidence_id} has unsupported source_class")
        observed_at = _aware_datetime(item.get("observed_at"), "evidence observed_at")
        if observed_at > as_of:
            raise ValueError(f"post-as-of evidence is not allowed: {evidence_id}")
        normalized = {
            "evidence_id": evidence_id,
            "source_id": source_id,
            "source_class": source_class,
            "observed_at": observed_at.isoformat(),
            "title": _required_text(item, "title"),
        }
        existing = result.get(evidence_id)
        if existing is not None and existing != normalized:
            raise ValueError(f"conflicting evidence ID: {evidence_id}")
        result[evidence_id] = normalized
    return result


def _linked_evidence(
    value: object,
    *,
    name: str,
    evidence: dict[str, dict[str, object]],
) -> tuple[list[str], set[str]]:
    ids = _string_list(value, name)
    unknown = sorted(set(ids) - set(evidence))
    if unknown:
        raise ValueError(f"{name} references unknown evidence: {','.join(unknown)}")
    classes = {str(evidence[item]["source_class"]) for item in ids}
    return ids, classes


def _normalize_company(
    raw: object,
    *,
    as_of: datetime,
    evidence: dict[str, dict[str, object]],
) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise ValueError("company must be an object")
    market_data_as_of = _aware_datetime(raw.get("market_data_as_of"), "market_data_as_of")
    if market_data_as_of > as_of:
        raise ValueError("company market data cannot be after scenario as_of")
    evidence_ids, _ = _linked_evidence(
        raw.get("evidence_ids"), name="company evidence_ids", evidence=evidence
    )
    return {
        "ticker": _required_text(raw, "ticker"),
        "company_name": _required_text(raw, "company_name"),
        "current_price": _number(raw.get("current_price"), "current_price", minimum=0.000001),
        "market_data_as_of": market_data_as_of.isoformat(),
        "shares_diluted": _number(raw.get("shares_diluted"), "shares_diluted", minimum=0.000001),
        "net_debt": _number(raw.get("net_debt"), "net_debt"),
        "baseline_forward_revenue": _number(
            raw.get("baseline_forward_revenue"), "baseline_forward_revenue", minimum=0
        ),
        "baseline_forward_operating_income": _number(
            raw.get("baseline_forward_operating_income"),
            "baseline_forward_operating_income",
        ),
        "baseline_forward_fcf": _number(raw.get("baseline_forward_fcf"), "baseline_forward_fcf"),
        "evidence_ids": evidence_ids,
    }


def _normalize_expectations(
    raw: object,
    *,
    as_of: datetime,
    evidence: dict[str, dict[str, object]],
) -> dict[int, dict[str, object]]:
    if not isinstance(raw, list):
        raise ValueError("market_expectations must be a list")
    result: dict[int, dict[str, object]] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"market_expectations[{index}] must be an object")
        horizon = _integer(item.get("horizon_months"), "expectation horizon_months")
        if horizon not in HORIZONS:
            raise ValueError(f"unsupported expectation horizon: {horizon}")
        if horizon in result:
            raise ValueError(f"duplicate market expectation horizon: {horizon}")
        expectation_as_of = _aware_datetime(item.get("as_of"), "market expectation as_of")
        if expectation_as_of > as_of:
            raise ValueError("market expectation cannot be after scenario as_of")
        evidence_ids, classes = _linked_evidence(
            item.get("evidence_ids"),
            name=f"market expectation {horizon} evidence_ids",
            evidence=evidence,
        )
        if "market_expectations" not in classes:
            raise ValueError(f"market expectation {horizon} requires market_expectations evidence")
        result[horizon] = {
            "horizon_months": horizon,
            "as_of": expectation_as_of.isoformat(),
            "forward_revenue": _number(item.get("forward_revenue"), "forward_revenue", minimum=0),
            "forward_operating_income": _number(
                item.get("forward_operating_income"), "forward_operating_income"
            ),
            "forward_fcf": _number(item.get("forward_fcf"), "forward_fcf"),
            "valuation_multiple": _number(
                item.get("valuation_multiple"), "valuation_multiple", minimum=0.000001
            ),
            "evidence_ids": evidence_ids,
        }
    if set(result) != set(HORIZONS):
        raise ValueError("market_expectations must contain exactly 6, 12, and 18 months")
    return result


def _normalize_cases(
    raw: object,
    *,
    evidence: dict[str, dict[str, object]],
) -> dict[tuple[str, int], dict[str, object]]:
    if not isinstance(raw, list):
        raise ValueError("cases must be a list")
    result: dict[tuple[str, int], dict[str, object]] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"cases[{index}] must be an object")
        scenario_id = _required_text(item, "scenario_id")
        if scenario_id not in SCENARIOS:
            raise ValueError(f"unsupported scenario_id: {scenario_id}")
        horizon = _integer(item.get("horizon_months"), "case horizon_months")
        if horizon not in HORIZONS:
            raise ValueError(f"unsupported case horizon: {horizon}")
        key = (scenario_id, horizon)
        if key in result:
            raise ValueError(f"duplicate case: {scenario_id}/{horizon}")
        posture = _required_text(item, "assumption_posture")
        if posture not in SOURCE_POSTURES:
            raise ValueError(f"unsupported assumption_posture: {posture}")
        evidence_ids, classes = _linked_evidence(
            item.get("evidence_ids"),
            name=f"case {scenario_id}/{horizon} evidence_ids",
            evidence=evidence,
        )
        if len(classes) < 2:
            raise ValueError(f"case {scenario_id}/{horizon} requires two source classes")
        confirmers = _string_list(
            item.get("confirmers_ko"), f"case {scenario_id}/{horizon} confirmers_ko"
        )
        falsifiers = _string_list(
            item.get("falsifiers_ko"), f"case {scenario_id}/{horizon} falsifiers_ko"
        )
        if any(len(value) < 10 for value in (*confirmers, *falsifiers)):
            raise ValueError("case confirmer and falsifier text must have at least 10 characters")
        price = _number(item.get("realized_price_per_unit"), "realized_price_per_unit", minimum=0)
        variable_cost = _number(
            item.get("variable_cost_per_unit"), "variable_cost_per_unit", minimum=0
        )
        if variable_cost > price:
            raise ValueError(f"case {scenario_id}/{horizon} variable cost exceeds price")
        result[key] = {
            "scenario_id": scenario_id,
            "horizon_months": horizon,
            "industry_incremental_demand_units": _number(
                item.get("industry_incremental_demand_units"),
                "industry_incremental_demand_units",
                minimum=0,
            ),
            "industry_incremental_supply_units": _number(
                item.get("industry_incremental_supply_units"),
                "industry_incremental_supply_units",
                minimum=0,
            ),
            "company_capture_share": _number(
                item.get("company_capture_share"),
                "company_capture_share",
                minimum=0,
                maximum=1,
            ),
            "company_available_incremental_capacity_units": _number(
                item.get("company_available_incremental_capacity_units"),
                "company_available_incremental_capacity_units",
                minimum=0,
            ),
            "realized_price_per_unit": price,
            "variable_cost_per_unit": variable_cost,
            "incremental_fixed_cost": _number(
                item.get("incremental_fixed_cost"), "incremental_fixed_cost", minimum=0
            ),
            "incremental_working_capital": _number(
                item.get("incremental_working_capital"),
                "incremental_working_capital",
                minimum=0,
            ),
            "incremental_capex": _number(
                item.get("incremental_capex"), "incremental_capex", minimum=0
            ),
            "tax_rate": _number(item.get("tax_rate"), "tax_rate", minimum=0, maximum=1),
            "valuation_multiple": _number(
                item.get("valuation_multiple"), "valuation_multiple", minimum=0.000001
            ),
            "assumption_posture": posture,
            "evidence_ids": evidence_ids,
            "evidence_classes": sorted(classes),
            "confirmers_ko": confirmers,
            "falsifiers_ko": falsifiers,
        }
    required = {(scenario, horizon) for scenario in SCENARIOS for horizon in HORIZONS}
    if set(result) != required:
        missing = sorted(required - set(result))
        extra = sorted(set(result) - required)
        raise ValueError(f"cases must contain the 3x3 scenario grid; missing={missing} extra={extra}")
    return result


def _normalize_catalysts(
    raw: object,
    *,
    as_of: datetime,
    evidence: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        raise ValueError("catalysts must be a list")
    result: list[dict[str, object]] = []
    ids: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"catalysts[{index}] must be an object")
        catalyst_id = _required_text(item, "catalyst_id")
        if catalyst_id in ids:
            raise ValueError(f"duplicate catalyst_id: {catalyst_id}")
        ids.add(catalyst_id)
        date_status = _required_text(item, "date_status")
        if date_status not in {"confirmed", "inferred"}:
            raise ValueError(f"catalyst {catalyst_id} has unsupported date_status")
        event_at = _aware_datetime(item.get("event_at"), "catalyst event_at")
        months = (event_at - as_of).total_seconds() / (30.4375 * 24 * 3600)
        if months < 0 or months > 18:
            raise ValueError(f"catalyst {catalyst_id} must occur within 18 months")
        evidence_ids, _ = _linked_evidence(
            item.get("evidence_ids"), name=f"catalyst {catalyst_id} evidence_ids", evidence=evidence
        )
        result.append(
            {
                "catalyst_id": catalyst_id,
                "title_ko": _required_text(item, "title_ko", minimum=10),
                "event_at": event_at.isoformat(),
                "date_status": date_status,
                "evidence_ids": evidence_ids,
            }
        )
    result.sort(key=lambda item: (str(item["event_at"]), str(item["catalyst_id"])))
    return result


def _validate_scenario_order(rows: list[dict[str, object]]) -> None:
    """Reject economically inverted downside/base/upside labels."""
    for horizon in HORIZONS:
        by_scenario = {
            str(row["scenario_id"]): row
            for row in rows
            if row["horizon_months"] == horizon
        }
        for metric in ("industry_incremental_demand_units", "implied_value_per_share"):
            values = [float(by_scenario[scenario][metric]) for scenario in SCENARIOS]
            if values != sorted(values):
                raise ValueError(
                    f"scenario ordering is inverted for {metric} at {horizon} months"
                )


def _investor_summary_ko(
    rows: list[dict[str, object]],
    assessments: list[dict[str, object]],
    *,
    company: dict[str, object],
    currency: str,
    volume_unit: str,
    decision: str,
    gate_reasons: list[str],
) -> dict[str, str]:
    base = next(
        row
        for row in rows
        if row["scenario_id"] == "base" and row["horizon_months"] == 12
    )
    assessment = next(item for item in assessments if item["horizon_months"] == 12)
    reward = assessment["reward_to_downside"]
    reward_text = "산정 불가" if reward is None else f"{float(reward):.2f}배"
    gate_text = "모든 정량 관문 통과" if not gate_reasons else ", ".join(gate_reasons)
    return {
        "bottleneck_to_revenue": (
            f"12개월 기준 시나리오에서 산업 수요와 공급의 차이는 "
            f"{float(base['industry_shortage_units']):,.2f} {volume_unit}이며, "
            f"{company['company_name']}가 실제로 확보할 수 있는 물량은 "
            f"{float(base['company_captured_volume_units']):,.2f} {volume_unit}로 제한했습니다. "
            f"이에 따른 증분 매출은 {float(base['incremental_revenue']):,.2f} {currency}입니다."
        ),
        "earnings_and_cash_flow": (
            f"해당 물량은 증분 영업이익 {float(base['incremental_operating_income']):,.2f} "
            f"{currency}, 증분 잉여현금흐름 {float(base['incremental_fcf']):,.2f} {currency}로 "
            "연결됩니다. 운전자본·설비투자·현금세금을 차감한 결과입니다."
        ),
        "market_expectations_gap": (
            f"12개월 예상 영업이익은 시장 기대보다 "
            f"{float(base['operating_income_gap_vs_market']):,.2f} {currency}, "
            f"잉여현금흐름은 {float(base['fcf_gap_vs_market']):,.2f} {currency} 높습니다. "
            f"현재 가격 대비 기준 시나리오 기대수익률은 "
            f"{float(base['expected_return']) * 100:.1f}%입니다."
        ),
        "risk_reward": (
            f"12개월 가격 수익률 범위는 하방 {float(assessment['downside_return']) * 100:.1f}%, "
            f"기준 {float(assessment['base_return']) * 100:.1f}%, "
            f"상방 {float(assessment['upside_return']) * 100:.1f}%이며, "
            f"기준 보상/하방 비율은 {reward_text}입니다."
        ),
        "research_decision": f"연구 상태는 {decision}이며 관문 결과는 {gate_text}입니다.",
    }


def _calculate_row(
    case: dict[str, object],
    *,
    company: dict[str, object],
    expectation: dict[str, object],
) -> dict[str, object]:
    demand = float(case["industry_incremental_demand_units"])
    supply = float(case["industry_incremental_supply_units"])
    shortage = max(demand - supply, 0.0)
    addressable_volume = shortage * float(case["company_capture_share"])
    captured_volume = min(
        addressable_volume, float(case["company_available_incremental_capacity_units"])
    )
    price = float(case["realized_price_per_unit"])
    variable_cost = float(case["variable_cost_per_unit"])
    incremental_revenue = captured_volume * price
    incremental_contribution = captured_volume * (price - variable_cost)
    incremental_operating_income = incremental_contribution - float(
        case["incremental_fixed_cost"]
    )
    cash_tax = max(incremental_operating_income, 0.0) * float(case["tax_rate"])
    incremental_fcf = (
        incremental_operating_income
        - cash_tax
        - float(case["incremental_working_capital"])
        - float(case["incremental_capex"])
    )

    projected_revenue = float(company["baseline_forward_revenue"]) + incremental_revenue
    projected_operating_income = (
        float(company["baseline_forward_operating_income"]) + incremental_operating_income
    )
    projected_fcf = float(company["baseline_forward_fcf"]) + incremental_fcf
    implied_enterprise_value = projected_operating_income * float(case["valuation_multiple"])
    implied_equity_value = max(implied_enterprise_value - float(company["net_debt"]), 0.0)
    implied_value_per_share = implied_equity_value / float(company["shares_diluted"])
    expected_return = implied_value_per_share / float(company["current_price"]) - 1
    market_multiple = float(expectation["valuation_multiple"])
    fundamental_only_ev = projected_operating_income * market_multiple
    fundamental_only_equity = max(fundamental_only_ev - float(company["net_debt"]), 0.0)
    fundamental_only_value_per_share = fundamental_only_equity / float(
        company["shares_diluted"]
    )

    operating_gap = projected_operating_income - float(expectation["forward_operating_income"])
    multiple_delta = float(case["valuation_multiple"]) - market_multiple
    if operating_gap > 0 and multiple_delta <= 0:
        upside_driver = "fundamentals"
    elif operating_gap > 0 and multiple_delta > 0:
        upside_driver = "fundamentals_and_multiple"
    elif operating_gap <= 0 and multiple_delta > 0:
        upside_driver = "multiple_expansion_only"
    else:
        upside_driver = "no_positive_variant_wedge"

    return {
        **case,
        "industry_shortage_units": round(shortage, 6),
        "company_addressable_volume_units": round(addressable_volume, 6),
        "company_captured_volume_units": round(captured_volume, 6),
        "incremental_revenue": round(incremental_revenue, 2),
        "incremental_contribution": round(incremental_contribution, 2),
        "incremental_operating_income": round(incremental_operating_income, 2),
        "incremental_cash_tax": round(cash_tax, 2),
        "incremental_fcf": round(incremental_fcf, 2),
        "projected_forward_revenue": round(projected_revenue, 2),
        "projected_forward_operating_income": round(projected_operating_income, 2),
        "projected_forward_fcf": round(projected_fcf, 2),
        "market_expected_forward_revenue": expectation["forward_revenue"],
        "market_expected_forward_operating_income": expectation["forward_operating_income"],
        "market_expected_forward_fcf": expectation["forward_fcf"],
        "revenue_gap_vs_market": round(
            projected_revenue - float(expectation["forward_revenue"]), 2
        ),
        "revenue_gap_pct_vs_market": _percentage_gap(
            projected_revenue, float(expectation["forward_revenue"])
        ),
        "operating_income_gap_vs_market": round(operating_gap, 2),
        "operating_income_gap_pct_vs_market": _percentage_gap(
            projected_operating_income, float(expectation["forward_operating_income"])
        ),
        "fcf_gap_vs_market": round(projected_fcf - float(expectation["forward_fcf"]), 2),
        "fcf_gap_pct_vs_market": _percentage_gap(
            projected_fcf, float(expectation["forward_fcf"])
        ),
        "market_valuation_multiple": market_multiple,
        "valuation_multiple_delta": round(multiple_delta, 4),
        "fundamental_only_value_per_share": round(fundamental_only_value_per_share, 4),
        "implied_value_per_share": round(implied_value_per_share, 4),
        "expected_return": round(expected_return, 6),
        "upside_driver": upside_driver,
    }


def _horizon_assessment(rows: list[dict[str, object]], horizon: int) -> dict[str, object]:
    by_scenario = {str(row["scenario_id"]): row for row in rows if row["horizon_months"] == horizon}
    downside_return = float(by_scenario["downside"]["expected_return"])
    base_return = float(by_scenario["base"]["expected_return"])
    upside_return = float(by_scenario["upside"]["expected_return"])
    reward_to_downside = None
    if downside_return < 0:
        reward_to_downside = round(max(base_return, 0.0) / abs(downside_return), 4)
    return {
        "horizon_months": horizon,
        "downside_return": downside_return,
        "base_return": base_return,
        "upside_return": upside_return,
        "reward_to_downside": reward_to_downside,
        "base_operating_income_gap_vs_market": by_scenario["base"][
            "operating_income_gap_vs_market"
        ],
        "base_fcf_gap_vs_market": by_scenario["base"]["fcf_gap_vs_market"],
        "base_upside_driver": by_scenario["base"]["upside_driver"],
    }


def _decision(
    assessment_12m: dict[str, object],
    *,
    senior_review_ready: bool,
    catalyst_count: int,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    base_return = float(assessment_12m["base_return"])
    downside_return = float(assessment_12m["downside_return"])
    reward_to_downside = assessment_12m["reward_to_downside"]
    operating_gap = float(assessment_12m["base_operating_income_gap_vs_market"])
    fcf_gap = float(assessment_12m["base_fcf_gap_vs_market"])

    if operating_gap <= 0 or fcf_gap <= 0:
        reasons.append("no_positive_12m_expectation_gap")
    if base_return < BASE_RETURN_HURDLE:
        reasons.append("base_return_below_hurdle")
    if downside_return < MAX_DOWNSIDE:
        reasons.append("downside_exceeds_limit")
    if reward_to_downside is None or float(reward_to_downside) < MIN_REWARD_TO_DOWNSIDE:
        reasons.append("reward_to_downside_below_hurdle")
    if catalyst_count < 2:
        reasons.append("insufficient_18m_catalysts")
    if not senior_review_ready:
        reasons.append("source_or_market_data_not_review_ready")

    if not reasons:
        return "advance_to_deeper_work", []
    if "no_positive_12m_expectation_gap" in reasons:
        return "reject_no_expectation_gap", reasons
    if "downside_exceeds_limit" in reasons or "reward_to_downside_below_hurdle" in reasons:
        return "reject_unfavorable_skew", reasons
    if "base_return_below_hurdle" in reasons:
        return "valuation_gated", reasons
    return "wait_for_proof", reasons


def build_bottleneck_financial_scenario(payload: dict[str, object]) -> dict[str, object]:
    if payload.get("schema_version") != FINANCIAL_SCENARIO_INPUT_SCHEMA:
        raise ValueError("unsupported bottleneck financial scenario input schema")
    if payload.get("period_basis") != "forward_annualized_at_horizon":
        raise ValueError("period_basis must be forward_annualized_at_horizon")
    scenario_run_id = _required_text(payload, "scenario_run_id")
    candidate_id = _required_text(payload, "candidate_id")
    node_id = _required_text(payload, "node_id")
    as_of = _aware_datetime(payload.get("as_of"), "scenario as_of")
    currency = _required_text(payload, "currency")
    volume_unit = _required_text(payload, "volume_unit")

    evidence = _evidence_index(payload.get("evidence"), as_of=as_of)
    company = _normalize_company(payload.get("company"), as_of=as_of, evidence=evidence)
    expectations = _normalize_expectations(
        payload.get("market_expectations"), as_of=as_of, evidence=evidence
    )
    cases = _normalize_cases(payload.get("cases"), evidence=evidence)
    catalysts = _normalize_catalysts(payload.get("catalysts"), as_of=as_of, evidence=evidence)

    rows = [
        _calculate_row(cases[(scenario, horizon)], company=company, expectation=expectations[horizon])
        for horizon in HORIZONS
        for scenario in SCENARIOS
    ]
    _validate_scenario_order(rows)
    assessments = [_horizon_assessment(rows, horizon) for horizon in HORIZONS]

    evidence_classes = {str(item["source_class"]) for item in evidence.values()}
    market_age_days = (
        as_of - datetime.fromisoformat(str(company["market_data_as_of"]))
    ).total_seconds() / 86400
    expectation_age_days = max(
        (as_of - datetime.fromisoformat(str(item["as_of"]))).total_seconds() / 86400
        for item in expectations.values()
    )
    senior_review_ready = (
        market_age_days <= 7
        and expectation_age_days <= 90
        and len(evidence_classes) >= 4
        and "market_expectations" in evidence_classes
    )
    assessment_12m = next(item for item in assessments if item["horizon_months"] == 12)
    decision, gate_reasons = _decision(
        assessment_12m,
        senior_review_ready=senior_review_ready,
        catalyst_count=len(catalysts),
    )
    investor_summary_ko = _investor_summary_ko(
        rows,
        assessments,
        company=company,
        currency=currency,
        volume_unit=volume_unit,
        decision=decision,
        gate_reasons=gate_reasons,
    )

    output: dict[str, object] = {
        "schema_version": FINANCIAL_SCENARIO_OUTPUT_SCHEMA,
        "scenario_run_id": scenario_run_id,
        "candidate_id": candidate_id,
        "node_id": node_id,
        "as_of": as_of.isoformat(),
        "currency": currency,
        "volume_unit": volume_unit,
        "period_basis": "forward_annualized_at_horizon",
        "strict_as_of": True,
        "security_level_recommendation": False,
        "company": company,
        "evidence": [evidence[key] for key in sorted(evidence)],
        "market_expectations": [expectations[horizon] for horizon in HORIZONS],
        "catalysts": catalysts,
        "scenario_rows": rows,
        "horizon_assessments": assessments,
        "investor_summary_ko": investor_summary_ko,
        "readiness": {
            "status": "senior_review_ready" if senior_review_ready else "screen_grade",
            "market_data_age_days": round(market_age_days, 2),
            "max_expectation_age_days": round(expectation_age_days, 2),
            "evidence_class_count": len(evidence_classes),
            "evidence_classes": sorted(evidence_classes),
        },
        "investment_research_decision": {
            "status": decision,
            "gate_reasons": gate_reasons,
            "hurdles": {
                "base_12m_return_min": BASE_RETURN_HURDLE,
                "downside_12m_return_min": MAX_DOWNSIDE,
                "reward_to_downside_min": MIN_REWARD_TO_DOWNSIDE,
                "catalysts_within_18m_min": 2,
            },
            "first_rejection": None if not gate_reasons else gate_reasons[0],
            "what_would_make_it_investable": list(
                cases[("base", 12)]["confirmers_ko"]
            ),
            "what_would_kill_it": list(cases[("downside", 12)]["falsifiers_ko"]),
        },
    }
    output["scenario_sha256"] = _canonical_sha256(output)
    return output


def write_bottleneck_financial_scenario(
    output_dir: Path, output: dict[str, object]
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "bottleneck_financial_scenario.json"
    csv_path = output_dir / "bottleneck_financial_scenario.csv"
    json_path.write_text(
        json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    rows = output["scenario_rows"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("scenario output has no rows")
    columns = [
        "scenario_id",
        "horizon_months",
        "industry_shortage_units",
        "company_captured_volume_units",
        "incremental_revenue",
        "incremental_operating_income",
        "incremental_fcf",
        "projected_forward_revenue",
        "projected_forward_operating_income",
        "projected_forward_fcf",
        "operating_income_gap_vs_market",
        "fcf_gap_vs_market",
        "fundamental_only_value_per_share",
        "implied_value_per_share",
        "expected_return",
        "upside_driver",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return json_path, csv_path
