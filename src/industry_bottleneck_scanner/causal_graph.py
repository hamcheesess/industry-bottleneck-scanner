from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .causal_expansion import CausalEvidence, ValueChainEdge

GRAPH_SCHEMA_VERSION = "causal-graph-v1"


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True)
class EdgeApproval:
    edge_id: str
    as_of: datetime
    edge: ValueChainEdge
    approved: bool
    reasons: tuple[str, ...]
    evidence_classes: tuple[str, ...]


def evaluate_edge(
    edge_id: str,
    edge: ValueChainEdge,
    *,
    as_of: datetime,
    min_independent_evidence_classes: int = 2,
    external_corroboration_required: bool = True,
) -> EdgeApproval:
    _require_aware("as_of", as_of)
    if not edge_id.strip():
        raise ValueError("edge_id is required")
    if min_independent_evidence_classes < 1:
        raise ValueError("min_independent_evidence_classes must be at least 1")

    future = [item.evidence_id for item in edge.evidence if item.observed_at > as_of]
    if future:
        raise ValueError(
            "look-ahead edge evidence after as_of is not allowed: "
            + ",".join(sorted(future))
        )

    evidence_classes = tuple(sorted({item.evidence_class for item in edge.evidence}))
    reasons: list[str] = []
    if len(evidence_classes) < min_independent_evidence_classes:
        reasons.append("insufficient_independent_evidence_classes")
    if external_corroboration_required and not any(
        item.externally_corroborating for item in edge.evidence
    ):
        reasons.append("no_external_corroboration")
    if not edge.mechanism.strip():
        reasons.append("missing_economic_mechanism")

    return EdgeApproval(
        edge_id=edge_id,
        as_of=as_of,
        edge=edge,
        approved=not reasons,
        reasons=tuple(reasons),
        evidence_classes=evidence_classes,
    )


def _evidence_to_dict(item: CausalEvidence) -> dict[str, object]:
    return {
        "evidence_id": item.evidence_id,
        "evidence_class": item.evidence_class,
        "source_id": item.source_id,
        "observed_at": item.observed_at.isoformat(),
        "summary": item.summary,
        "beneficiary_company_id": item.beneficiary_company_id,
        "source_company_id": item.source_company_id,
    }


def _evidence_from_dict(raw: dict[str, object]) -> CausalEvidence:
    return CausalEvidence(
        evidence_id=str(raw["evidence_id"]),
        evidence_class=str(raw["evidence_class"]),  # type: ignore[arg-type]
        source_id=str(raw["source_id"]),
        observed_at=datetime.fromisoformat(str(raw["observed_at"])),
        summary=str(raw["summary"]),
        beneficiary_company_id=(
            None if raw.get("beneficiary_company_id") is None else str(raw["beneficiary_company_id"])
        ),
        source_company_id=(
            None if raw.get("source_company_id") is None else str(raw["source_company_id"])
        ),
    )


def approval_to_dict(item: EdgeApproval) -> dict[str, object]:
    edge = item.edge
    return {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "edge_id": item.edge_id,
        "as_of": item.as_of.isoformat(),
        "approved": item.approved,
        "reasons": list(item.reasons),
        "evidence_classes": list(item.evidence_classes),
        "edge": {
            "upstream_node": edge.upstream_node,
            "downstream_node": edge.downstream_node,
            "relation": edge.relation,
            "mechanism": edge.mechanism,
            "demand_sensitivity": edge.demand_sensitivity,
            "lag_months_min": edge.lag_months_min,
            "lag_months_max": edge.lag_months_max,
            "evidence": [_evidence_to_dict(evidence) for evidence in edge.evidence],
        },
    }


def approval_from_dict(payload: dict[str, object]) -> EdgeApproval:
    if payload.get("schema_version") != GRAPH_SCHEMA_VERSION:
        raise ValueError(f"unsupported causal-graph schema: {payload.get('schema_version')!r}")
    raw_edge = payload.get("edge")
    if not isinstance(raw_edge, dict):
        raise ValueError("edge must be an object")
    raw_evidence = raw_edge.get("evidence")
    if not isinstance(raw_evidence, list):
        raise ValueError("edge evidence must be a list")
    edge = ValueChainEdge(
        upstream_node=str(raw_edge["upstream_node"]),
        downstream_node=str(raw_edge["downstream_node"]),
        relation=str(raw_edge["relation"]),  # type: ignore[arg-type]
        mechanism=str(raw_edge["mechanism"]),
        demand_sensitivity=int(raw_edge["demand_sensitivity"]),
        lag_months_min=(
            None if raw_edge.get("lag_months_min") is None else int(raw_edge["lag_months_min"])
        ),
        lag_months_max=(
            None if raw_edge.get("lag_months_max") is None else int(raw_edge["lag_months_max"])
        ),
        evidence=tuple(_evidence_from_dict(raw) for raw in raw_evidence if isinstance(raw, dict)),
    )
    return EdgeApproval(
        edge_id=str(payload["edge_id"]),
        as_of=datetime.fromisoformat(str(payload["as_of"])),
        edge=edge,
        approved=bool(payload["approved"]),
        reasons=tuple(str(item) for item in payload.get("reasons", [])),  # type: ignore[arg-type]
        evidence_classes=tuple(str(item) for item in payload.get("evidence_classes", [])),  # type: ignore[arg-type]
    )


class FileCausalGraphStore:
    """Append-only approval history for reusable economic dependency edges."""

    def __init__(self, path: Path):
        self.path = path

    def append(self, approval: EdgeApproval) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(approval_to_dict(approval), sort_keys=True) + "\n")

    def load(self) -> tuple[EdgeApproval, ...]:
        if not self.path.exists():
            return ()
        rows: list[EdgeApproval] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{self.path}:{line_number}: invalid JSON") from exc
                if not isinstance(payload, dict):
                    raise ValueError(f"{self.path}:{line_number}: graph row must be an object")
                rows.append(approval_from_dict(payload))
        rows.sort(key=lambda item: (item.edge_id, item.as_of))
        return tuple(rows)

    def latest_as_of(self, *, as_of: datetime) -> tuple[EdgeApproval, ...]:
        _require_aware("as_of", as_of)
        latest: dict[str, EdgeApproval] = {}
        for item in self.load():
            if item.as_of <= as_of:
                previous = latest.get(item.edge_id)
                if previous is None or item.as_of > previous.as_of:
                    latest[item.edge_id] = item
        return tuple(latest[key] for key in sorted(latest))

    def approved_edges_as_of(self, *, as_of: datetime) -> tuple[ValueChainEdge, ...]:
        return tuple(item.edge for item in self.latest_as_of(as_of=as_of) if item.approved)


def reachable_paths(
    root_node: str,
    edges: Iterable[ValueChainEdge],
    *,
    max_depth: int = 4,
) -> tuple[tuple[str, ...], ...]:
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1")
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.upstream_node, []).append(edge.downstream_node)
    for downstream in adjacency.values():
        downstream.sort()

    paths: list[tuple[str, ...]] = []

    def walk(path: tuple[str, ...]) -> None:
        if len(path) - 1 >= max_depth:
            return
        current = path[-1]
        for next_node in adjacency.get(current, []):
            if next_node in path:
                continue
            next_path = path + (next_node,)
            paths.append(next_path)
            walk(next_path)

    walk((root_node,))
    return tuple(paths)
