from datetime import datetime, timezone

import pytest

from industry_bottleneck_scanner.causal_expansion import (
    CausalEvidence,
    NodeAssessment,
    ValueChainEdge,
    rank_node,
    rank_nodes,
)


AS_OF = datetime(2026, 1, 15, tzinfo=timezone.utc)


def evidence(
    evidence_id: str,
    evidence_class: str,
    *,
    source_company_id: str | None,
    beneficiary_company_id: str = "BENEFICIARY",
    observed_at: datetime = AS_OF,
) -> CausalEvidence:
    return CausalEvidence(
        evidence_id=evidence_id,
        evidence_class=evidence_class,  # type: ignore[arg-type]
        source_id=f"source:{evidence_id}",
        observed_at=observed_at,
        summary=evidence_id,
        beneficiary_company_id=beneficiary_company_id,
        source_company_id=source_company_id,
    )


def test_pre_news_candidate_requires_strong_economics_and_expectation_gap() -> None:
    assessment = NodeAssessment(
        node_id="high-voltage-equipment",
        as_of=AS_OF,
        demand_transmission=5,
        bottleneck_strength=5,
        economic_capture=4,
        reinvestment_runway=4,
        triangulation=4,
        expectation_gap=4,
        evidence=(
            evidence("customer-capex", "customer_capex_plan", source_company_id="CUSTOMER"),
            evidence("lead-time", "lead_time_constraint", source_company_id="SUPPLIER"),
            evidence("industry", "physical_industry_data", source_company_id=None),
        ),
    )

    ranked = rank_node(assessment)
    assert ranked.stage == "pre_news_candidate"
    assert ranked.score >= 70
    assert ranked.gate_reasons == ()


def test_high_score_cannot_bypass_weak_causal_or_evidence_gates() -> None:
    assessment = NodeAssessment(
        node_id="story-only-node",
        as_of=AS_OF,
        demand_transmission=2,
        bottleneck_strength=5,
        economic_capture=5,
        reinvestment_runway=5,
        triangulation=5,
        expectation_gap=5,
        evidence=(
            evidence(
                "self-commentary",
                "management_operating_commentary",
                source_company_id="BENEFICIARY",
            ),
        ),
    )

    ranked = rank_node(assessment)
    assert ranked.stage == "hypothesis"
    assert "weak_demand_transmission" in ranked.gate_reasons
    assert "insufficient_independent_evidence_classes" in ranked.gate_reasons
    assert "no_external_corroboration" in ranked.gate_reasons


def test_evidence_backed_node_can_rank_without_being_a_bottleneck() -> None:
    assessment = NodeAssessment(
        node_id="generic-construction-input",
        as_of=AS_OF,
        demand_transmission=4,
        bottleneck_strength=1,
        economic_capture=1,
        reinvestment_runway=3,
        triangulation=3,
        expectation_gap=4,
        evidence=(
            evidence("customer-buildout", "customer_capacity_plan", source_company_id="CUSTOMER"),
            evidence("industry-data", "physical_industry_data", source_company_id=None),
        ),
    )

    ranked = rank_node(assessment)
    assert ranked.stage == "evidence_backed"


def test_as_of_rejects_look_ahead_evidence() -> None:
    future = datetime(2026, 2, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="look-ahead"):
        NodeAssessment(
            node_id="late-confirmation",
            as_of=AS_OF,
            demand_transmission=5,
            bottleneck_strength=5,
            economic_capture=5,
            reinvestment_runway=5,
            triangulation=5,
            expectation_gap=5,
            evidence=(
                evidence(
                    "later-contract",
                    "customer_capacity_plan",
                    source_company_id="CUSTOMER",
                    observed_at=future,
                ),
                evidence("older-industry-data", "physical_industry_data", source_company_id=None),
            ),
        )


def test_rank_nodes_prioritizes_stage_before_raw_score() -> None:
    priority = NodeAssessment(
        node_id="priority",
        as_of=AS_OF,
        demand_transmission=4,
        bottleneck_strength=4,
        economic_capture=4,
        reinvestment_runway=4,
        triangulation=4,
        expectation_gap=1,
        evidence=(
            evidence("capex", "customer_capex_plan", source_company_id="CUSTOMER"),
            evidence("lead", "lead_time_constraint", source_company_id="SUPPLIER"),
        ),
    )
    hypothesis = NodeAssessment(
        node_id="hypothesis",
        as_of=AS_OF,
        demand_transmission=2,
        bottleneck_strength=5,
        economic_capture=5,
        reinvestment_runway=5,
        triangulation=5,
        expectation_gap=5,
        evidence=(
            evidence("only-one", "management_operating_commentary", source_company_id="BENEFICIARY"),
        ),
    )

    ranked = rank_nodes((hypothesis, priority))
    assert [item.node_id for item in ranked] == ["priority", "hypothesis"]


def test_value_chain_edge_validates_score_and_lag_order() -> None:
    edge = ValueChainEdge(
        upstream_node="ai-compute",
        downstream_node="data-center-power",
        relation="requires_capacity",
        mechanism="incremental compute capacity requires additional electrical infrastructure",
        demand_sensitivity=5,
        lag_months_min=6,
        lag_months_max=24,
    )
    assert edge.demand_sensitivity == 5

    with pytest.raises(ValueError, match="demand_sensitivity"):
        ValueChainEdge(
            upstream_node="a",
            downstream_node="b",
            relation="requires_input",
            mechanism="x",
            demand_sensitivity=6,
        )

    with pytest.raises(ValueError, match="lag_months_min"):
        ValueChainEdge(
            upstream_node="a",
            downstream_node="b",
            relation="requires_input",
            mechanism="x",
            demand_sensitivity=3,
            lag_months_min=12,
            lag_months_max=6,
        )
