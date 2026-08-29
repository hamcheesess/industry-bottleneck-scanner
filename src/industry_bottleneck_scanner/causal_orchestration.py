from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .causal_expansion import CausalEvidence, ValueChainEdge
from .causal_graph import FileCausalGraphStore, reachable_paths
from .demand_convergence import (
    DemandBranch,
    DemandConvergenceAssessment,
    assess_demand_convergence,
)
from .industry_state import FileIndustryStateRegistry
from .root_demand_shock import FileRootShockStore, RootDemandShock


@dataclass(frozen=True)
class CausalConvergenceRun:
    trigger_root_shock_id: str
    as_of: datetime
    root_shock_ids: tuple[str, ...]
    branches: tuple[DemandBranch, ...]
    assessments: tuple[DemandConvergenceAssessment, ...]


def _branch_id(root_shock_id: str, path_nodes: tuple[str, ...]) -> str:
    payload = f"{root_shock_id}|{'|'.join(path_nodes)}"
    return "branch-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _unique_evidence(items: Iterable[CausalEvidence]) -> tuple[CausalEvidence, ...]:
    by_id: dict[str, CausalEvidence] = {}
    for item in items:
        existing = by_id.get(item.evidence_id)
        if existing is not None and existing != item:
            raise ValueError(f"conflicting causal evidence ID: {item.evidence_id}")
        by_id[item.evidence_id] = item
    return tuple(by_id[key] for key in sorted(by_id))


def _validate_independent_root_shocks(shocks: tuple[RootDemandShock, ...]) -> None:
    """Reject renamed or evidence-reused roots before convergence can count them twice."""

    root_by_node: dict[str, str] = {}
    evidence_owner: dict[str, str] = {}
    for shock in sorted(shocks, key=lambda item: item.root_shock_id):
        existing_root = root_by_node.get(shock.root_node)
        if existing_root is not None and existing_root != shock.root_shock_id:
            raise ValueError(
                "distinct root_shock_id values cannot share one root_node: "
                f"{existing_root},{shock.root_shock_id}"
            )
        root_by_node[shock.root_node] = shock.root_shock_id
        for evidence in shock.evidence:
            existing_owner = evidence_owner.get(evidence.evidence_id)
            if existing_owner is not None and existing_owner != shock.root_shock_id:
                raise ValueError(
                    "independent root shocks cannot reuse root evidence: "
                    f"{evidence.evidence_id}"
                )
            evidence_owner[evidence.evidence_id] = shock.root_shock_id


def branches_from_root_shocks(
    shocks: Iterable[RootDemandShock],
    edges: Iterable[ValueChainEdge],
    *,
    as_of: datetime,
    max_depth: int = 4,
) -> tuple[DemandBranch, ...]:
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    shock_items = tuple(shocks)
    _validate_independent_root_shocks(shock_items)
    edge_items = tuple(edges)
    by_segment: dict[tuple[str, str], list[ValueChainEdge]] = {}
    for edge in edge_items:
        by_segment.setdefault((edge.upstream_node, edge.downstream_node), []).append(edge)

    branches: dict[str, DemandBranch] = {}
    for shock in shock_items:
        if shock.as_of > as_of:
            raise ValueError("root shock as_of cannot exceed branch as_of")
        paths = tuple(dict.fromkeys(reachable_paths(shock.root_node, edge_items, max_depth=max_depth)))
        for path in paths:
            segment_edges = [
                by_segment[(upstream, downstream)]
                for upstream, downstream in zip(path, path[1:])
            ]
            segment_strengths = [max(edge.demand_sensitivity for edge in choices) for choices in segment_edges]
            transmission_strength = min((shock.demand_strength, *segment_strengths))
            evidence = _unique_evidence(
                (
                    *shock.evidence,
                    *(
                        item
                        for choices in segment_edges
                        for edge in choices
                        for item in edge.evidence
                    ),
                )
            )
            branch_id = _branch_id(shock.root_shock_id, path)
            branches[branch_id] = DemandBranch(
                branch_id=branch_id,
                root_shock_id=shock.root_shock_id,
                root_node=shock.root_node,
                target_node=path[-1],
                as_of=as_of,
                transmission_strength=transmission_strength,
                path_nodes=path,
                evidence=evidence,
            )
    return tuple(sorted(branches.values(), key=lambda item: item.branch_id))


def run_causal_convergence(
    *,
    root_store: FileRootShockStore,
    graph_store: FileCausalGraphStore,
    state_registry: FileIndustryStateRegistry,
    trigger_root_shock_id: str,
    as_of: datetime,
    max_depth: int = 4,
) -> CausalConvergenceRun:
    shocks = root_store.approved_shocks_as_of(as_of=as_of)
    shocks_by_id = {item.root_shock_id: item for item in shocks}
    trigger = shocks_by_id.get(trigger_root_shock_id)
    if trigger is None:
        raise ValueError("trigger root shock is not approved as of the requested timestamp")
    edges = graph_store.approved_edges_as_of(as_of=as_of)
    branches = branches_from_root_shocks(shocks, edges, as_of=as_of, max_depth=max_depth)
    trigger_targets = {
        item.target_node for item in branches if item.root_shock_id == trigger_root_shock_id
    }
    assessments = tuple(
        assess_demand_convergence(
            (item for item in branches if item.target_node == target_node),
            trigger_root_shock_id=trigger_root_shock_id,
            trigger_detected_at=trigger.detected_at,
            as_of=as_of,
            state_registry=state_registry,
        )
        for target_node in sorted(trigger_targets)
    )
    return CausalConvergenceRun(
        trigger_root_shock_id=trigger_root_shock_id,
        as_of=as_of,
        root_shock_ids=tuple(sorted(shocks_by_id)),
        branches=branches,
        assessments=assessments,
    )


def _evidence_reference(item: CausalEvidence) -> dict[str, object]:
    return {
        "evidence_id": item.evidence_id,
        "evidence_class": item.evidence_class,
        "source_id": item.source_id,
        "observed_at": item.observed_at.isoformat(),
    }


def branch_to_dict(branch: DemandBranch) -> dict[str, object]:
    return {
        "schema_version": "demand-branch-v1",
        "branch_id": branch.branch_id,
        "root_shock_id": branch.root_shock_id,
        "root_node": branch.root_node,
        "target_node": branch.target_node,
        "as_of": branch.as_of.isoformat(),
        "transmission_strength": branch.transmission_strength,
        "path_nodes": list(branch.path_nodes),
        "evidence": [_evidence_reference(item) for item in branch.evidence],
    }


def assessment_to_dict(assessment: DemandConvergenceAssessment) -> dict[str, object]:
    state = assessment.pre_shock_state
    return {
        "schema_version": "demand-convergence-assessment-v1",
        "node_id": assessment.node_id,
        "as_of": assessment.as_of.isoformat(),
        "trigger_detected_at": assessment.trigger_detected_at.isoformat(),
        "trigger_root_shock_id": assessment.trigger_root_shock_id,
        "branch_ids": [item.branch_id for item in assessment.branches],
        "independent_root_shock_ids": list(assessment.independent_root_shock_ids),
        "evidence_classes": list(assessment.evidence_classes),
        "trigger_transmission_strength": assessment.trigger_transmission_strength,
        "score": assessment.score,
        "stage": assessment.stage,
        "gate_reasons": list(assessment.gate_reasons),
        "pre_shock_state": (
            None
            if state is None
            else {
                "node_id": state.node_id,
                "as_of": state.as_of.isoformat(),
                "stage": state.stage,
                "constraint_score": state.constraint_score,
            }
        ),
    }


def write_causal_convergence_artifacts(
    output_dir: Path,
    run: CausalConvergenceRun,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    branches_path = output_dir / "demand_branches.jsonl"
    temporary_branches = branches_path.with_suffix(".jsonl.tmp")
    with temporary_branches.open("w", encoding="utf-8") as handle:
        for branch in run.branches:
            handle.write(json.dumps(branch_to_dict(branch), sort_keys=True) + "\n")
    os.replace(temporary_branches, branches_path)

    convergence_path = output_dir / "demand_convergence.json"
    temporary_convergence = convergence_path.with_suffix(".json.tmp")
    temporary_convergence.write_text(
        json.dumps(
            {
                "schema_version": "causal-convergence-run-v1",
                "trigger_root_shock_id": run.trigger_root_shock_id,
                "as_of": run.as_of.isoformat(),
                "root_shock_ids": list(run.root_shock_ids),
                "branch_count": len(run.branches),
                "assessment_count": len(run.assessments),
                "assessments": [assessment_to_dict(item) for item in run.assessments],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_convergence, convergence_path)
    return branches_path, convergence_path
