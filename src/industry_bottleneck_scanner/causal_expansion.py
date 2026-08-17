from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Literal

EvidenceClass = Literal[
    "customer_capex_plan",
    "customer_capacity_plan",
    "customer_architecture_dependency",
    "supplier_capacity_expansion",
    "lead_time_constraint",
    "qualification_barrier",
    "pricing_or_repricing",
    "physical_industry_data",
    "management_operating_commentary",
    "competitor_corroboration",
]

RelationType = Literal[
    "requires_input",
    "requires_capacity",
    "capacity_enabler",
    "complement",
    "substitute",
    "distribution_or_service",
    "physical_constraint",
]

ResearchStage = Literal[
    "hypothesis",
    "evidence_backed",
    "priority_research",
    "pre_news_candidate",
]


@dataclass(frozen=True)
class CausalEvidence:
    evidence_id: str
    evidence_class: EvidenceClass
    source_id: str
    observed_at: datetime
    summary: str
    beneficiary_company_id: str | None = None
    source_company_id: str | None = None

    @property
    def externally_corroborating(self) -> bool:
        if self.beneficiary_company_id is None:
            return True
        if self.source_company_id is None:
            return True
        return self.source_company_id != self.beneficiary_company_id


@dataclass(frozen=True)
class ValueChainEdge:
    upstream_node: str
    downstream_node: str
    relation: RelationType
    mechanism: str
    demand_sensitivity: int
    lag_months_min: int | None = None
    lag_months_max: int | None = None
    evidence: tuple[CausalEvidence, ...] = ()

    def __post_init__(self) -> None:
        _validate_score("demand_sensitivity", self.demand_sensitivity)
        if self.lag_months_min is not None and self.lag_months_min < 0:
            raise ValueError("lag_months_min must be non-negative")
        if self.lag_months_max is not None and self.lag_months_max < 0:
            raise ValueError("lag_months_max must be non-negative")
        if (
            self.lag_months_min is not None
            and self.lag_months_max is not None
            and self.lag_months_min > self.lag_months_max
        ):
            raise ValueError("lag_months_min cannot exceed lag_months_max")


@dataclass(frozen=True)
class NodeAssessment:
    node_id: str
    as_of: datetime
    demand_transmission: int
    bottleneck_strength: int
    economic_capture: int
    reinvestment_runway: int
    triangulation: int
    expectation_gap: int
    evidence: tuple[CausalEvidence, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "demand_transmission",
            "bottleneck_strength",
            "economic_capture",
            "reinvestment_runway",
            "triangulation",
            "expectation_gap",
        ):
            _validate_score(name, getattr(self, name))
        future = [item.evidence_id for item in self.evidence if item.observed_at > self.as_of]
        if future:
            raise ValueError(f"look-ahead evidence after as_of is not allowed: {','.join(sorted(future))}")

    @property
    def independent_evidence_classes(self) -> tuple[str, ...]:
        return tuple(sorted({item.evidence_class for item in self.evidence}))

    @property
    def has_external_corroboration(self) -> bool:
        return any(item.externally_corroborating for item in self.evidence)


@dataclass(frozen=True)
class RankedNode:
    node_id: str
    stage: ResearchStage
    score: float
    gate_reasons: tuple[str, ...]
    evidence_classes: tuple[str, ...]


DEFAULT_WEIGHTS: dict[str, float] = {
    "demand_transmission": 0.20,
    "bottleneck_strength": 0.20,
    "economic_capture": 0.20,
    "reinvestment_runway": 0.15,
    "triangulation": 0.15,
    "expectation_gap": 0.10,
}


def _validate_score(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
        raise ValueError(f"{name} must be an integer from 0 to 5")


def _weighted_score(assessment: NodeAssessment) -> float:
    weighted = sum(getattr(assessment, name) * weight for name, weight in DEFAULT_WEIGHTS.items())
    return round(weighted / 5.0 * 100.0, 2)


def rank_node(assessment: NodeAssessment) -> RankedNode:
    reasons: list[str] = []
    evidence_classes = assessment.independent_evidence_classes

    if assessment.demand_transmission < 3:
        reasons.append("weak_demand_transmission")
    if len(evidence_classes) < 2:
        reasons.append("insufficient_independent_evidence_classes")
    if not assessment.has_external_corroboration:
        reasons.append("no_external_corroboration")

    score = _weighted_score(assessment)
    if reasons:
        stage: ResearchStage = "hypothesis"
    elif (
        assessment.bottleneck_strength >= 3
        and assessment.economic_capture >= 3
        and assessment.triangulation >= 3
    ):
        if assessment.expectation_gap >= 3 and score >= 70:
            stage = "pre_news_candidate"
        else:
            stage = "priority_research"
    else:
        stage = "evidence_backed"

    return RankedNode(
        node_id=assessment.node_id,
        stage=stage,
        score=score,
        gate_reasons=tuple(reasons),
        evidence_classes=evidence_classes,
    )


def rank_nodes(assessments: Iterable[NodeAssessment]) -> tuple[RankedNode, ...]:
    ranked = [rank_node(item) for item in assessments]
    stage_order: dict[ResearchStage, int] = {
        "pre_news_candidate": 3,
        "priority_research": 2,
        "evidence_backed": 1,
        "hypothesis": 0,
    }
    ranked.sort(key=lambda item: (stage_order[item.stage], item.score, item.node_id), reverse=True)
    return tuple(ranked)
