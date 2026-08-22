from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from industry_bottleneck_scanner.causal_expansion import CausalEvidence, ValueChainEdge
from industry_bottleneck_scanner.causal_graph import FileCausalGraphStore, evaluate_edge
from industry_bottleneck_scanner.causal_convergence_cli import main
from industry_bottleneck_scanner.causal_orchestration import (
    run_causal_convergence,
    write_causal_convergence_artifacts,
)
from industry_bottleneck_scanner.industry_state import FileIndustryStateRegistry, IndustryStateSnapshot
from industry_bottleneck_scanner.root_demand_shock import (
    FileRootShockStore,
    RootDemandShock,
    evaluate_root_demand_shock,
)


PRE = datetime(2026, 7, 1, tzinfo=timezone.utc)
TRIGGER = datetime(2026, 8, 10, tzinfo=timezone.utc)
AS_OF = datetime(2026, 8, 11, tzinfo=timezone.utc)
TARGET = "large-power-transformers"


def evidence(name: str, evidence_class: str, observed_at: datetime = PRE) -> CausalEvidence:
    return CausalEvidence(
        evidence_id=name,
        evidence_class=evidence_class,  # type: ignore[arg-type]
        source_id=f"source-{name}",
        observed_at=observed_at,
        summary=name,
    )


def root(root_id: str, root_node: str, detected_at: datetime) -> RootDemandShock:
    return RootDemandShock(
        root_shock_id=root_id,
        root_node=root_node,
        label=f"Concrete demand expansion for {root_node}",
        mechanism=f"New capacity at {root_node} raises equipment demand.",
        market_trigger_id=f"trigger:{root_id}",
        market_bucket="Electrical Equipment",
        detected_at=detected_at,
        as_of=AS_OF,
        demand_strength=5,
        evidence=(
            evidence(f"{root_id}-plan", "customer_capacity_plan", detected_at),
            evidence(f"{root_id}-physical", "physical_industry_data", detected_at),
        ),
    )


def edge(upstream: str, downstream: str, name: str, strength: int = 5) -> ValueChainEdge:
    return ValueChainEdge(
        upstream_node=upstream,
        downstream_node=downstream,
        relation="requires_capacity",
        mechanism=f"{upstream} requires {downstream} capacity",
        demand_sensitivity=strength,
        evidence=(
            evidence(f"{name}-architecture", "customer_architecture_dependency"),
            evidence(f"{name}-supplier", "supplier_capacity_expansion"),
        ),
    )


def stores(tmp_path: Path):
    roots = FileRootShockStore(tmp_path / "roots.jsonl")
    for item in (
        root("grid-modernization", "grid-hardening-program", PRE),
        root("cloud-capacity", "cloud-data-center-expansion", PRE),
        root("ai-inference", "ai-inference-compute-deployment", TRIGGER),
    ):
        roots.append(evaluate_root_demand_shock(item))

    graph = FileCausalGraphStore(tmp_path / "graph.jsonl")
    graph_edges = (
        edge("grid-hardening-program", TARGET, "grid", 4),
        edge("cloud-data-center-expansion", TARGET, "cloud", 4),
        edge("ai-inference-compute-deployment", "data-center-power", "ai-power", 5),
        edge("data-center-power", TARGET, "power-transformer", 5),
    )
    for index, item in enumerate(graph_edges):
        graph.append(evaluate_edge(f"edge-{index}", item, as_of=AS_OF))

    states = FileIndustryStateRegistry(tmp_path / "state.jsonl")
    states.append(
        IndustryStateSnapshot(
            node_id=TARGET,
            as_of=PRE,
            supply_inelasticity=5,
            lead_time_pressure=5,
            capacity_tightness=5,
            capacity_expansion_difficulty=5,
            qualification_barrier=5,
            pricing_pressure=4,
            evidence=(
                evidence("state-lead", "lead_time_constraint"),
                evidence("state-capacity", "capacity_utilization"),
                evidence("state-physical", "physical_industry_data"),
            ),
        )
    )
    return roots, graph, states


def test_orchestration_builds_approved_paths_and_priority_convergence(tmp_path: Path) -> None:
    roots, graph, states = stores(tmp_path)
    run = run_causal_convergence(
        root_store=roots,
        graph_store=graph,
        state_registry=states,
        trigger_root_shock_id="ai-inference",
        as_of=AS_OF,
    )

    target = next(item for item in run.assessments if item.node_id == TARGET)
    ai_branch = next(
        item
        for item in run.branches
        if item.root_shock_id == "ai-inference" and item.target_node == TARGET
    )
    assert ai_branch.path_nodes == (
        "ai-inference-compute-deployment",
        "data-center-power",
        TARGET,
    )
    assert ai_branch.transmission_strength == 5
    assert target.independent_root_count == 3
    assert target.stage == "priority_convergence"
    assert target.pre_shock_state is not None
    assert target.pre_shock_state.as_of == PRE

    branches_path, convergence_path = write_causal_convergence_artifacts(tmp_path / "out", run)
    branch_rows = [json.loads(line) for line in branches_path.read_text().splitlines()]
    convergence = json.loads(convergence_path.read_text())
    assert all(item["schema_version"] == "demand-branch-v1" for item in branch_rows)
    assert convergence["schema_version"] == "causal-convergence-run-v1"
    assert convergence["assessment_count"] == len(run.assessments)


def test_graph_revision_after_as_of_cannot_leak_into_replay(tmp_path: Path) -> None:
    roots, graph, states = stores(tmp_path)
    future_edge = edge("ai-inference-compute-deployment", "future-only-node", "future")
    graph.append(
        evaluate_edge(
            "future-edge",
            future_edge,
            as_of=AS_OF + timedelta(days=1),
        )
    )

    run = run_causal_convergence(
        root_store=roots,
        graph_store=graph,
        state_registry=states,
        trigger_root_shock_id="ai-inference",
        as_of=AS_OF,
    )

    assert all(item.target_node != "future-only-node" for item in run.branches)


def test_causal_convergence_cli_writes_versioned_artifacts(tmp_path: Path) -> None:
    roots, graph, states = stores(tmp_path)
    output = tmp_path / "cli-output"

    assert main(
        [
            "--root-shock-registry",
            str(roots.path),
            "--causal-graph-registry",
            str(graph.path),
            "--industry-state-registry",
            str(states.path),
            "--trigger-root-shock-id",
            "ai-inference",
            "--as-of",
            AS_OF.isoformat(),
            "--output-dir",
            str(output),
        ]
    ) == 0

    payload = json.loads((output / "demand_convergence.json").read_text())
    assert payload["schema_version"] == "causal-convergence-run-v1"
    assert any(item["node_id"] == TARGET for item in payload["assessments"])
