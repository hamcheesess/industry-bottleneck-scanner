from datetime import datetime, timezone
from pathlib import Path

from industry_bottleneck_scanner.causal_expansion import CausalEvidence
from industry_bottleneck_scanner.demand_convergence import DemandBranch, assess_demand_convergence
from industry_bottleneck_scanner.industry_state import FileIndustryStateRegistry, IndustryStateSnapshot


PRE = datetime(2023, 4, 1, tzinfo=timezone.utc)
TRIGGER = datetime(2023, 4, 25, tzinfo=timezone.utc)
AS_OF = datetime(2023, 5, 5, tzinfo=timezone.utc)


def evidence(evidence_id: str, evidence_class: str, observed_at: datetime = PRE) -> CausalEvidence:
    return CausalEvidence(
        evidence_id=evidence_id,
        evidence_class=evidence_class,  # type: ignore[arg-type]
        source_id=f"source:{evidence_id}",
        observed_at=observed_at,
        summary=evidence_id,
    )


def state(*, node_id: str = "large-power-transformers", constrained: bool = True, as_of: datetime = PRE):
    level = 5 if constrained else 1
    return IndustryStateSnapshot(
        node_id=node_id,
        as_of=as_of,
        supply_inelasticity=level,
        lead_time_pressure=level,
        capacity_tightness=level,
        capacity_expansion_difficulty=level,
        qualification_barrier=level,
        pricing_pressure=level,
        evidence=(
            evidence("state-lead", "lead_time_constraint"),
            evidence("state-capacity", "supplier_capacity_expansion"),
            evidence("state-physical", "physical_industry_data"),
        ),
    )


def branch(
    branch_id: str,
    root_shock_id: str,
    root_node: str,
    strength: int,
    evidence_class: str,
) -> DemandBranch:
    return DemandBranch(
        branch_id=branch_id,
        root_shock_id=root_shock_id,
        root_node=root_node,
        target_node="large-power-transformers",
        as_of=AS_OF,
        transmission_strength=strength,
        path_nodes=(root_node, "data-center-or-grid-capacity", "large-power-transformers"),
        evidence=(evidence(branch_id, evidence_class, observed_at=AS_OF),),
    )


def registry(tmp_path: Path, snapshot: IndustryStateSnapshot) -> FileIndustryStateRegistry:
    result = FileIndustryStateRegistry(tmp_path / "state.jsonl")
    result.append(snapshot)
    return result


def test_new_ai_branch_joining_existing_roots_at_constrained_node_is_priority_convergence(tmp_path: Path) -> None:
    branches = (
        branch("grid", "grid-modernization", "grid-modernization", 4, "physical_industry_data"),
        branch("cloud", "cloud-capacity", "cloud-capacity", 4, "customer_capacity_plan"),
        branch("ai", "ai-inference", "ai-inference", 5, "customer_capex_plan"),
    )
    result = assess_demand_convergence(
        branches,
        trigger_root_shock_id="ai-inference",
        trigger_detected_at=TRIGGER,
        as_of=AS_OF,
        state_registry=registry(tmp_path, state()),
    )

    assert result.stage == "priority_convergence"
    assert result.independent_root_count == 3
    assert result.other_root_count == 2
    assert result.pre_shock_state is not None
    assert result.pre_shock_state.stage == "severely_constrained"
    assert result.score >= 70
    assert result.gate_reasons == ()


def test_multiple_paths_from_same_root_do_not_fake_branch_diversity(tmp_path: Path) -> None:
    branches = (
        branch("ai-a", "ai-inference", "ai-inference", 5, "customer_capex_plan"),
        branch("ai-b", "ai-inference", "ai-inference", 4, "customer_architecture_dependency"),
    )
    result = assess_demand_convergence(
        branches,
        trigger_root_shock_id="ai-inference",
        trigger_detected_at=TRIGGER,
        as_of=AS_OF,
        state_registry=registry(tmp_path, state()),
    )

    assert result.independent_root_count == 1
    assert result.stage == "pre_shock_bottleneck"


def test_normal_pre_shock_supply_state_blocks_convergence_promotion(tmp_path: Path) -> None:
    result = assess_demand_convergence(
        (
            branch("grid", "grid-modernization", "grid-modernization", 4, "physical_industry_data"),
            branch("ai", "ai-inference", "ai-inference", 5, "customer_capex_plan"),
        ),
        trigger_root_shock_id="ai-inference",
        trigger_detected_at=TRIGGER,
        as_of=AS_OF,
        state_registry=registry(tmp_path, state(constrained=False)),
    )

    assert result.stage == "hypothesis"
    assert "pre_shock_state_not_constrained" in result.gate_reasons


def test_post_trigger_state_is_not_usable_as_pre_shock_evidence(tmp_path: Path) -> None:
    post_trigger = datetime(2023, 4, 30, tzinfo=timezone.utc)
    result = assess_demand_convergence(
        (branch("ai", "ai-inference", "ai-inference", 5, "customer_capex_plan"),),
        trigger_root_shock_id="ai-inference",
        trigger_detected_at=TRIGGER,
        as_of=AS_OF,
        state_registry=registry(tmp_path, state(as_of=post_trigger)),
    )

    assert result.stage == "hypothesis"
    assert result.pre_shock_state is None
    assert "missing_pre_shock_state" in result.gate_reasons


def test_weak_trigger_branch_does_not_promote_old_bottleneck(tmp_path: Path) -> None:
    result = assess_demand_convergence(
        (
            branch("grid", "grid-modernization", "grid-modernization", 5, "physical_industry_data"),
            branch("ai", "ai-inference", "ai-inference", 2, "customer_capex_plan"),
        ),
        trigger_root_shock_id="ai-inference",
        trigger_detected_at=TRIGGER,
        as_of=AS_OF,
        state_registry=registry(tmp_path, state()),
    )

    assert result.stage == "hypothesis"
    assert "weak_trigger_transmission" in result.gate_reasons
