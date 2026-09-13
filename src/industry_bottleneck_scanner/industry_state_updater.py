from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Literal, Mapping

from .causal_expansion import CausalEvidence, EvidenceClass
from .industry_state import (
    STATE_WEIGHTS,
    FileIndustryStateRegistry,
    IndustryStateSnapshot,
    snapshot_to_dict,
)
from .models import AtomicSignal

StateDimension = Literal[
    "supply_inelasticity",
    "lead_time_pressure",
    "capacity_tightness",
    "capacity_expansion_difficulty",
    "qualification_barrier",
    "pricing_pressure",
]


@dataclass(frozen=True)
class SignalStateRule:
    dimension: StateDimension
    score: int
    evidence_class: EvidenceClass
    eligible_direction: str


SIGNAL_STATE_RULES: dict[str, SignalStateRule] = {
    "lead_time_pressure": SignalStateRule(
        "lead_time_pressure", 4, "lead_time_constraint", "strengthening"
    ),
    "capacity_constraint": SignalStateRule(
        "capacity_tightness", 4, "capacity_utilization", "strengthening"
    ),
    "sold_out_capacity": SignalStateRule(
        "capacity_tightness", 5, "capacity_utilization", "strengthening"
    ),
    "supply_tightness": SignalStateRule(
        "supply_inelasticity", 4, "management_operating_commentary", "strengthening"
    ),
    "allocation": SignalStateRule(
        "supply_inelasticity", 5, "management_operating_commentary", "strengthening"
    ),
    "qualification_barrier": SignalStateRule(
        "qualification_barrier", 4, "qualification_barrier", "strengthening"
    ),
    "pricing_power": SignalStateRule(
        "pricing_pressure", 3, "pricing_or_repricing", "strengthening"
    ),
    "contract_repricing": SignalStateRule(
        "pricing_pressure", 4, "pricing_or_repricing", "strengthening"
    ),
    "margin_from_pricing": SignalStateRule(
        "pricing_pressure", 4, "pricing_or_repricing", "strengthening"
    ),
    "pricing_weakness": SignalStateRule(
        "pricing_pressure", 1, "pricing_or_repricing", "weakening"
    ),
}


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _validate_score(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
        raise ValueError("observation score must be an integer from 0 to 5")


@dataclass(frozen=True)
class IndustryStateObservation:
    observation_id: str
    node_id: str
    dimension: StateDimension
    score: int
    observed_at: datetime
    evidence: CausalEvidence

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("observation_id is required")
        if not self.node_id.strip():
            raise ValueError("node_id is required")
        if self.dimension not in STATE_WEIGHTS:
            raise ValueError(f"unsupported state dimension: {self.dimension}")
        _validate_score(self.score)
        _require_aware("observed_at", self.observed_at)
        _require_aware("evidence.observed_at", self.evidence.observed_at)
        if self.evidence.observed_at != self.observed_at:
            raise ValueError("observation and evidence timestamps must match")


@dataclass(frozen=True)
class IndustryStateUpdatePolicy:
    min_independent_evidence_classes: int = 2
    min_independent_sources: int = 2

    def __post_init__(self) -> None:
        if self.min_independent_evidence_classes < 1:
            raise ValueError("min_independent_evidence_classes must be at least 1")
        if self.min_independent_sources < 1:
            raise ValueError("min_independent_sources must be at least 1")


@dataclass(frozen=True)
class IndustryStateUpdateDecision:
    node_id: str
    as_of: datetime
    approved: bool
    reasons: tuple[str, ...]
    new_observation_ids: tuple[str, ...]
    independent_evidence_classes: tuple[str, ...]
    independent_source_ids: tuple[str, ...]
    independent_source_entities: tuple[str, ...]
    previous_as_of: datetime | None
    snapshot: IndustryStateSnapshot


def observation_to_dict(observation: IndustryStateObservation) -> dict[str, object]:
    evidence = observation.evidence
    return {
        "schema_version": "industry-state-observation-v1",
        "observation_id": observation.observation_id,
        "node_id": observation.node_id,
        "dimension": observation.dimension,
        "score": observation.score,
        "observed_at": observation.observed_at.isoformat(),
        "evidence": {
            "evidence_id": evidence.evidence_id,
            "evidence_class": evidence.evidence_class,
            "source_id": evidence.source_id,
            "observed_at": evidence.observed_at.isoformat(),
            "summary": evidence.summary,
            "beneficiary_company_id": evidence.beneficiary_company_id,
            "source_company_id": evidence.source_company_id,
        },
    }


def observation_from_dict(payload: Mapping[str, object]) -> IndustryStateObservation:
    if payload.get("schema_version") != "industry-state-observation-v1":
        raise ValueError(f"unsupported industry-state observation schema: {payload.get('schema_version')!r}")
    raw_evidence = payload.get("evidence")
    if not isinstance(raw_evidence, dict):
        raise ValueError("industry-state observation evidence must be an object")
    evidence = CausalEvidence(
        evidence_id=str(raw_evidence["evidence_id"]),
        evidence_class=str(raw_evidence["evidence_class"]),  # type: ignore[arg-type]
        source_id=str(raw_evidence["source_id"]),
        observed_at=datetime.fromisoformat(str(raw_evidence["observed_at"])),
        summary=str(raw_evidence["summary"]),
        beneficiary_company_id=(
            None
            if raw_evidence.get("beneficiary_company_id") is None
            else str(raw_evidence["beneficiary_company_id"])
        ),
        source_company_id=(
            None
            if raw_evidence.get("source_company_id") is None
            else str(raw_evidence["source_company_id"])
        ),
    )
    return IndustryStateObservation(
        observation_id=str(payload["observation_id"]),
        node_id=str(payload["node_id"]),
        dimension=str(payload["dimension"]),  # type: ignore[arg-type]
        score=int(payload["score"]),
        observed_at=datetime.fromisoformat(str(payload["observed_at"])),
        evidence=evidence,
    )


def decision_to_dict(decision: IndustryStateUpdateDecision) -> dict[str, object]:
    return {
        "schema_version": "industry-state-update-decision-v1",
        "node_id": decision.node_id,
        "as_of": decision.as_of.isoformat(),
        "approved": decision.approved,
        "reasons": list(decision.reasons),
        "new_observation_ids": list(decision.new_observation_ids),
        "independent_evidence_classes": list(decision.independent_evidence_classes),
        "independent_source_ids": list(decision.independent_source_ids),
        "independent_source_entities": list(decision.independent_source_entities),
        "previous_as_of": decision.previous_as_of.isoformat() if decision.previous_as_of else None,
        "snapshot": snapshot_to_dict(decision.snapshot),
    }


def observation_from_atomic_signal(
    signal: AtomicSignal,
    *,
    node_id: str,
) -> IndustryStateObservation | None:
    """Map eligible issuer-language signals to a value-chain node explicitly.

    The caller supplies the economic node assignment. Static industry labels and tickers are
    never silently promoted into causal node identity.
    """

    if signal.negated or signal.resolved:
        return None
    rule = SIGNAL_STATE_RULES.get(signal.metric)
    if rule is None or signal.direction != rule.eligible_direction:
        return None
    evidence = CausalEvidence(
        evidence_id=f"state-evidence:{signal.signal_id}",
        evidence_class=rule.evidence_class,
        source_id=signal.document_id,
        observed_at=signal.published_at,
        summary=signal.evidence_text,
        beneficiary_company_id=signal.company_id,
        source_company_id=signal.company_id,
    )
    return IndustryStateObservation(
        observation_id=f"state-observation:{signal.signal_id}:{node_id}",
        node_id=node_id,
        dimension=rule.dimension,
        score=rule.score,
        observed_at=signal.published_at,
        evidence=evidence,
    )


def observations_from_atomic_signals(
    signals: Iterable[AtomicSignal],
    *,
    company_node_assignments: Mapping[str, Iterable[str]],
) -> tuple[IndustryStateObservation, ...]:
    observations: list[IndustryStateObservation] = []
    for signal in signals:
        for node_id in sorted(set(company_node_assignments.get(signal.company_id, ()))):
            observation = observation_from_atomic_signal(signal, node_id=node_id)
            if observation is not None:
                observations.append(observation)
    return tuple(observations)


def _rounded_mean(values: Iterable[int]) -> int:
    items = tuple(values)
    return int(sum(items) / len(items) + 0.5)


def evaluate_industry_state_update(
    *,
    node_id: str,
    as_of: datetime,
    observations: Iterable[IndustryStateObservation],
    previous: IndustryStateSnapshot | None = None,
    policy: IndustryStateUpdatePolicy = IndustryStateUpdatePolicy(),
) -> IndustryStateUpdateDecision:
    _require_aware("as_of", as_of)
    if not node_id.strip():
        raise ValueError("node_id is required")
    if previous is not None:
        if previous.node_id != node_id:
            raise ValueError("previous snapshot node does not match update node")
        if previous.as_of >= as_of:
            raise ValueError("previous snapshot must be strictly earlier than update as_of")

    items = tuple(item for item in observations if item.node_id == node_id)
    ids = [item.observation_id for item in items]
    if len(set(ids)) != len(ids):
        raise ValueError("industry-state observations must have unique observation IDs")
    future = [item.observation_id for item in items if item.observed_at > as_of]
    if future:
        raise ValueError("look-ahead state observations are not allowed: " + ",".join(sorted(future)))

    by_dimension: dict[str, list[int]] = {name: [] for name in STATE_WEIGHTS}
    for item in items:
        by_dimension[item.dimension].append(item.score)
    scores = {
        name: (
            _rounded_mean(by_dimension[name])
            if by_dimension[name]
            else getattr(previous, name) if previous is not None else 0
        )
        for name in STATE_WEIGHTS
    }

    evidence_by_id: dict[str, CausalEvidence] = {}
    if previous is not None:
        evidence_by_id.update((item.evidence_id, item) for item in previous.evidence)
    for item in items:
        existing = evidence_by_id.get(item.evidence.evidence_id)
        if existing is not None and existing != item.evidence:
            raise ValueError(f"conflicting state evidence ID: {item.evidence.evidence_id}")
        evidence_by_id[item.evidence.evidence_id] = item.evidence
    evidence = tuple(sorted(evidence_by_id.values(), key=lambda item: item.evidence_id))
    evidence_classes = tuple(sorted({item.evidence_class for item in evidence}))
    source_ids = tuple(sorted({item.source_id for item in evidence}))
    source_entities = tuple(
        sorted(
            {
                f"company:{item.source_company_id}"
                if item.source_company_id is not None
                else f"source:{item.source_id}"
                for item in evidence
            }
        )
    )

    snapshot = IndustryStateSnapshot(
        node_id=node_id,
        as_of=as_of,
        evidence=evidence,
        **scores,
    )
    reasons: list[str] = []
    if not items:
        reasons.append("no_new_state_observations")
    if len(evidence_classes) < policy.min_independent_evidence_classes:
        reasons.append("insufficient_independent_evidence_classes")
    if len(source_entities) < policy.min_independent_sources:
        reasons.append("insufficient_independent_sources")
    if previous is not None:
        same_scores = all(getattr(previous, name) == getattr(snapshot, name) for name in STATE_WEIGHTS)
        same_evidence = {item.evidence_id for item in previous.evidence} == set(evidence_by_id)
        if same_scores and same_evidence:
            reasons.append("no_state_change")

    return IndustryStateUpdateDecision(
        node_id=node_id,
        as_of=as_of,
        approved=not reasons,
        reasons=tuple(reasons),
        new_observation_ids=tuple(sorted(ids)),
        independent_evidence_classes=evidence_classes,
        independent_source_ids=source_ids,
        independent_source_entities=source_entities,
        previous_as_of=previous.as_of if previous is not None else None,
        snapshot=snapshot,
    )


def update_industry_state_registry(
    registry: FileIndustryStateRegistry,
    *,
    node_id: str,
    as_of: datetime,
    observations: Iterable[IndustryStateObservation],
    policy: IndustryStateUpdatePolicy = IndustryStateUpdatePolicy(),
) -> IndustryStateUpdateDecision:
    if any(item.node_id == node_id and item.as_of == as_of for item in registry.load()):
        raise ValueError("industry-state snapshot already exists for node_id and as_of")
    previous = registry.latest_before(node_id=node_id, cutoff=as_of, strict=True)
    decision = evaluate_industry_state_update(
        node_id=node_id,
        as_of=as_of,
        observations=observations,
        previous=previous,
        policy=policy,
    )
    if decision.approved:
        registry.append(decision.snapshot)
    return decision
