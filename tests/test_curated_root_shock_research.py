from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = (
    REPO_ROOT / "experiments" / "root_shock_research" / "18026c3fad8436f03022.json"
)
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "root-shock-adjudication.yml"
EDGE_PATH = (
    REPO_ROOT
    / "experiments"
    / "causal_edges"
    / "ai-data-center-load-to-grid-interconnection.json"
)


def test_first_curated_root_shock_result_is_provider_free_and_pre_cutoff() -> None:
    payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "root-shock-research-result-v1"
    assert payload["packet_id"] == "18026c3fad8436f03022"
    as_of = datetime.fromisoformat(payload["as_of"])
    assert as_of.tzinfo is not None

    shock = payload["root_shock"]
    assert shock["root_shock_id"] == "ai-data-center-electric-load-expansion-2026q3"
    assert shock["root_node"] == "ai-data-center-electric-load-growth"
    assert datetime.fromisoformat(shock["detected_at"]) <= as_of
    assert len(set(shock["causal_chain"])) >= 2

    evidence = shock["evidence"]
    packet_signals = {
        item["packet_signal_id"] for item in evidence if "packet_signal_id" in item
    }
    assert packet_signals == {
        "500fbd0c0eb3a17aa6579bd2",
        "9d437d52959ffb9763e1bfe0",
    }
    external = [item for item in evidence if "observed_at" in item]
    assert {item["source_category"] for item in external} == {
        "government_statistic",
        "regulatory_record",
    }
    assert all(datetime.fromisoformat(item["observed_at"]) <= as_of for item in external)
    assert {item["evidence_class"] for item in evidence} == {
        "backlog_or_orders",
        "physical_industry_data",
        "regulatory_or_permitting",
    }


def test_registry_workflow_keeps_adjudication_before_append() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    adjudicate = workflow.index("ibs-root-shock-research-adjudicate")
    append = workflow.index("ibs-root-shock-append")
    assert adjudicate < append
    assert "root_shock_input.json" in workflow[append:]
    assert "continue-on-error" not in workflow
    assert "actions: read" in workflow
    assert "contents: read" in workflow


def test_reused_root_and_edge_evidence_has_one_canonical_payload() -> None:
    root = json.loads(RESULT_PATH.read_text(encoding="utf-8"))["root_shock"]
    edge = json.loads(EDGE_PATH.read_text(encoding="utf-8"))["edge"]
    root_by_id = {item["evidence_id"]: item for item in root["evidence"]}

    for item in edge["evidence"]:
        root_item = root_by_id[item["evidence_id"]]
        assert item["evidence_class"] == root_item["evidence_class"]
        assert item["summary"] == root_item["summary"]
        if "source_id" in root_item:
            assert item["source_id"] == root_item["source_id"]
            assert item["observed_at"] == root_item["observed_at"]
        else:
            assert item["source_id"] == f"packet-signal:{root_item['packet_signal_id']}"
