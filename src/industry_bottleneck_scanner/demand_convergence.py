from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Literal

from .causal_expansion import CausalEvidence
from .industry_state import FileIndustryStateRegistry, IndustryStateSnapshot

ConvergenceStage = Literal[
    "hypothesis",
    "pre_shock_bottleneck",
    "multi_branch_convergence",
    "priority_convergence",
]


def _validate_score(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
        raise ValueError(f"{name} must be an integer from 0 to 5")


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True)
class DemandBranch:
    """One economically distinct demand root reaching a shared value-chain node.

    Multiple paths from the same root shock are deliberately deduplicated later by
    `root_shock_id`; they are not allowed to masquerade as independent demand branches.
    """

    branch_id: str
    root_shock_id: str
    root_node: str
    target_node: str
    as_of: datetime
    transmission_strength: int
    path_nodes: tuple[str, ...]
    evidence: tuple[CausalEvidence, ...] = ()

    def __post_init__(self) -> None:
        _require_aware("as_of", self.as_of)
        _validate_score("transmission_strength", self.transmission_strength)
        for name, value in (
            ("branch_id", self.branch_id),
            ("root_shock_id", self.root_shock_id),
            ("root_node", self.root_node),
            ("target_node", self.target_node),
        ):
            if not value.strip():
                raise ValueError(f"{name} is required")
        if not self.path_nodes:
            raise ValueError("path_nodes must not be empty")
        if self.path_nodes[0] != self.root_node:
            raise ValueError("path_nodes must start at root_node")
        if self.path_nodes[-1] != self.target_node:
            raise ValueError("path_nodes must end at target_node")
        future = [item.evidence_id for item in self.evidence if item.observed_at > self.as_of]
        if future:
            raise ValueError(
                "look-ahead evidence after branch as_of is not allowed: "
                + ",".join(sorted(future))
            )

    @property
    def evidence_classes(self) -> tuple[str, ...]:
        return tuple(sorted({item.evidence_class for item in self.evidence}))


@dataclass(frozen=True)
class DemandConvergenceAssessment:
    node_id: str
    as_of: datetime
    trigger_detected_at: datetime
    trigger_root_shock_id: str
    pre_shock_state: IndustryStateSnapshot | None
    branches: tuple[DemandBranch, ...]
    independent_root_shock_ids: tuple[str, ...]
    evidence_classes: tuple[str, ...]
    trigger_transmission_strength: int
    score: float
    stage: ConvergenceStage
    gate_reasons: tuple[str, ...]

    @property
    def independent_root_count(self) -> int:
        return len(self.independent_root_shock_ids)

    @property
    def other_root_count(self) -> int:
        return len([item for item in self.independent_root_shock_ids if item != self.trigger_root_shock_id])


def _score(
    *,
    trigger_strength: int,
    pre_shock_state: IndustryStateSnapshot | None,
    root_count: int,
    evidence_class_count: int,
) -> float:
    trigger_component = trigger_strength / 5.0 * 30.0
    constraint_component = (pre_shock_state.constraint_score if pre_shock_state else 0.0) * 0.35
    root_diversity = min(max(root_count - 1, 0) / 3.0, 1.0) * 20.0
    evidence_diversity = min(evidence_class_count / 4.0, 1.0) * 15.0
    return round(trigger_component + constraint_component + root_diversity + evidence_diversity, 2)


def assess_demand_convergence(
    branches: Iterable[DemandBranch],
    *,
    trigger_root_shock_id: str,
    trigger_detected_at: datetime,
    as_of: datetime,
    state_registry: FileIndustryStateRegistry,
) -> DemandConvergenceAssessment:
    _require_aware("trigger_detected_at", trigger_detected_at)
    _require_aware("as_of", as_of)
    if as_of < trigger_detected_at:
        raise ValueError("as_of cannot precede trigger_detected_at")

    items = tuple(branches)
    if not items:
        raise ValueError("at least one demand branch is required")
    targets = {item.target_node for item in items}
    if len(targets) != 1:
        raise ValueError("all demand branches in one assessment must share the same target node")
    if any(item.as_of > as_of for item in items):
        raise ValueError("branch as_of cannot exceed convergence assessment as_of")

    node_id = items[0].target_node
    pre_state = state_registry.latest_before(
        node_id=node_id,
        cutoff=trigger_detected_at,
        strict=True,
    )
    root_ids = tuple(sorted({item.root_shock_id for item in items}))
    evidence_classes = tuple(
        sorted({evidence.evidence_class for item in items for evidence in item.evidence})
    )
    trigger_strength = max(
        (item.transmission_strength for item in items if item.root_shock_id == trigger_root_shock_id),
        default=0,
    )

    reasons: list[str] = []
    if pre_state is None:
        reasons.append("missing_pre_shock_state")
    elif pre_state.stage not in {"constrained", "severely_constrained"}:
        reasons.append("pre_shock_state_not_constrained")
    if trigger_root_shock_id not in root_ids:
        reasons.append("missing_trigger_branch")
    elif trigger_strength < 3:
        reasons.append("weak_trigger_transmission")

    score = _score(
        trigger_strength=trigger_strength,
        pre_shock_state=pre_state,
        root_count=len(root_ids),
        evidence_class_count=len(evidence_classes),
    )

    if reasons:
        stage: ConvergenceStage = "hypothesis"
    elif len(root_ids) == 1:
        stage = "pre_shock_bottleneck"
    elif score >= 70 and trigger_strength >= 4:
        stage = "priority_convergence"
    else:
        stage = "multi_branch_convergence"

    return DemandConvergenceAssessment(
        node_id=node_id,
        as_of=as_of,
        trigger_detected_at=trigger_detected_at,
        trigger_root_shock_id=trigger_root_shock_id,
        pre_shock_state=pre_state,
        branches=items,
        independent_root_shock_ids=root_ids,
        evidence_classes=evidence_classes,
        trigger_transmission_strength=trigger_strength,
        score=score,
        stage=stage,
        gate_reasons=tuple(reasons),
    )
