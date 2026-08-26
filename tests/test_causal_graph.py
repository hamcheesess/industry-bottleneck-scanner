import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from industry_bottleneck_scanner.causal_expansion import CausalEvidence, ValueChainEdge
from industry_bottleneck_scanner.causal_graph import (
    FileCausalGraphStore,
    edge_input_from_dict,
    evaluate_edge,
    reachable_paths,
)
from industry_bottleneck_scanner.causal_edge_cli import main


AS_OF = datetime(2023, 4, 1, tzinfo=timezone.utc)
REPO_ROOT = Path(__file__).resolve().parents[1]


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


def edge(*, downstream: str = "data-center-power", evidence_rows=()) -> ValueChainEdge:
    return ValueChainEdge(
        upstream_node="ai-compute",
        downstream_node=downstream,
        relation="requires_capacity",
        mechanism="incremental AI compute requires additional data-center electrical capacity",
        demand_sensitivity=5,
        evidence=tuple(evidence_rows),
    )


def test_edge_requires_independent_classes_and_external_corroboration() -> None:
    approved = evaluate_edge(
        "ai-to-power",
        edge(
            evidence_rows=(
                evidence("customer", "customer_capex_plan", source_company_id="CUSTOMER"),
                evidence("physical", "physical_industry_data", source_company_id=None),
            )
        ),
        as_of=AS_OF,
    )
    assert approved.approved is True
    assert approved.reasons == ()

    rejected = evaluate_edge(
        "self-only",
        edge(
            evidence_rows=(
                evidence(
                    "self-a",
                    "management_operating_commentary",
                    source_company_id="BENEFICIARY",
                ),
                evidence(
                    "self-b",
                    "management_operating_commentary",
                    source_company_id="BENEFICIARY",
                ),
            )
        ),
        as_of=AS_OF,
    )
    assert rejected.approved is False
    assert "insufficient_independent_evidence_classes" in rejected.reasons
    assert "no_external_corroboration" in rejected.reasons


def test_edge_approval_rejects_look_ahead_evidence() -> None:
    future = datetime(2023, 5, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="look-ahead"):
        evaluate_edge(
            "future",
            edge(
                evidence_rows=(
                    evidence("old", "customer_capex_plan", source_company_id="CUSTOMER"),
                    evidence(
                        "later-contract",
                        "physical_industry_data",
                        source_company_id=None,
                        observed_at=future,
                    ),
                )
            ),
            as_of=AS_OF,
        )


def test_graph_store_uses_latest_approval_state_as_of_cutoff(tmp_path: Path) -> None:
    store = FileCausalGraphStore(tmp_path / "graph.jsonl")
    approved = evaluate_edge(
        "edge-1",
        edge(
            evidence_rows=(
                evidence("customer", "customer_capex_plan", source_company_id="CUSTOMER"),
                evidence("physical", "physical_industry_data", source_company_id=None),
            )
        ),
        as_of=AS_OF,
    )
    store.append(approved)

    later = datetime(2023, 6, 1, tzinfo=timezone.utc)
    rejected = evaluate_edge(
        "edge-1",
        edge(
            evidence_rows=(
                CausalEvidence(
                    evidence_id="self",
                    evidence_class="management_operating_commentary",
                    source_id="source:self",
                    observed_at=later,
                    summary="self",
                    beneficiary_company_id="BENEFICIARY",
                    source_company_id="BENEFICIARY",
                ),
            )
        ),
        as_of=later,
    )
    store.append(rejected)

    assert len(store.approved_edges_as_of(as_of=AS_OF)) == 1
    assert store.approved_edges_as_of(as_of=later) == ()
    with pytest.raises(ValueError, match="already exists"):
        store.append(approved)


def test_reachable_paths_support_branching_and_avoid_cycles() -> None:
    edges = (
        ValueChainEdge("ai", "data-center", "requires_capacity", "a", 5),
        ValueChainEdge("data-center", "power", "requires_capacity", "b", 5),
        ValueChainEdge("data-center", "cooling", "requires_capacity", "c", 4),
        ValueChainEdge("power", "transformers", "requires_input", "d", 4),
        ValueChainEdge("transformers", "data-center", "capacity_enabler", "cycle", 3),
    )
    paths = reachable_paths("ai", edges, max_depth=4)

    assert ("ai", "data-center", "power", "transformers") in paths
    assert ("ai", "data-center", "cooling") in paths
    assert all(len(path) == len(set(path)) for path in paths)


def test_curated_edge_cli_appends_provider_free_approved_revision(tmp_path: Path) -> None:
    input_path = (
        REPO_ROOT
        / "experiments"
        / "causal_edges"
        / "ai-data-center-load-to-grid-interconnection.json"
    )
    registry_path = tmp_path / "graph.jsonl"
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    edge_id, as_of, parsed_edge = edge_input_from_dict(payload)

    assert edge_id == "ai-data-center-load-requires-grid-interconnection"
    assert parsed_edge.upstream_node == "ai-data-center-electric-load-growth"
    assert parsed_edge.downstream_node == "large-load-grid-interconnection-capacity"
    assert {item.evidence_class for item in parsed_edge.evidence} == {
        "backlog_or_orders",
        "physical_industry_data",
        "regulatory_or_permitting",
    }
    assert all(item.observed_at <= as_of for item in parsed_edge.evidence)

    assert main(["--input", str(input_path), "--registry", str(registry_path)]) == 0
    approvals = FileCausalGraphStore(registry_path).latest_as_of(as_of=as_of)
    assert len(approvals) == 1
    assert approvals[0].approved is True
    assert approvals[0].reasons == ()


def test_causal_edge_cli_rejects_unsupported_input_schema(tmp_path: Path) -> None:
    input_path = tmp_path / "edge.json"
    input_path.write_text(json.dumps({"schema_version": "wrong"}), encoding="utf-8")

    with pytest.raises(SystemExit, match="unsupported causal-edge input schema"):
        main(["--input", str(input_path), "--registry", str(tmp_path / "graph.jsonl")])


def test_causal_edge_workflow_is_bounded_and_fail_closed() -> None:
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "causal-edge-adjudication.yml"
    ).read_text(encoding="utf-8")

    assert "ibs-causal-edge-append" in workflow
    assert "causal-graph-registry-${{ github.run_id }}" in workflow
    assert "edge_input_path must stay inside" in workflow
    assert "actions: read" in workflow
    assert "contents: read" in workflow
    assert "continue-on-error" not in workflow
