from __future__ import annotations

import ast
import json
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "industry_bottleneck_scanner"
REPO_ROOT = Path(__file__).resolve().parents[1]

ACTIVE_CAUSAL_MODULES = (
    "market_history.py",
    "market_trigger.py",
    "market_trigger_calibration.py",
    "market_trigger_quality.py",
    "market_trigger_research_queue.py",
    "causal_diagnosis.py",
    "causal_expansion.py",
    "causal_graph.py",
    "causal_orchestration.py",
    "industry_state.py",
    "root_demand_shock.py",
    "demand_convergence.py",
    "pre_news_replay.py",
    "operating_evidence_batch.py",
    "causal_diagnosis_batch.py",
    "operating_signal_quality.py",
)

PARKED_PROVIDER_MODULES = {
    "quartr",
    "transcript_fallback",
    "v2_source_provenance",
}

ACTIVE_PROVIDER_MODULES = {
    "alpha_vantage",
    "eod_market_data",
    "massive_universe",
    "quartr",
    "sec_edgar",
}


def _local_import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level and module:
                roots.add(module.split(".")[0])
            elif module.startswith("industry_bottleneck_scanner."):
                roots.add(module.split(".", 1)[1].split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name.startswith("industry_bottleneck_scanner."):
                    roots.add(name.split(".", 1)[1].split(".")[0])
    return roots


def _active_policy() -> dict[str, object]:
    return json.loads(
        (REPO_ROOT / "experiments" / "market_triggered_discovery_policy.draft.json").read_text(
            encoding="utf-8"
        )
    )


def test_active_causal_modules_do_not_depend_on_parked_quartr_path() -> None:
    violations: dict[str, list[str]] = {}
    for name in ACTIVE_CAUSAL_MODULES:
        imports = _local_import_roots(PACKAGE_ROOT / name)
        bad = sorted(imports & PARKED_PROVIDER_MODULES)
        if bad:
            violations[name] = bad
    assert violations == {}


def test_active_causal_modules_do_not_import_provider_adapters() -> None:
    violations: dict[str, list[str]] = {}
    for name in ACTIVE_CAUSAL_MODULES:
        imports = _local_import_roots(PACKAGE_ROOT / name)
        bad = sorted(imports & ACTIVE_PROVIDER_MODULES)
        if bad:
            violations[name] = bad
    assert violations == {}


def test_active_policy_supersedes_transcript_v2_without_rewriting_frozen_v1() -> None:
    active = _active_policy()
    legacy = json.loads(
        (REPO_ROOT / "experiments" / "v2_validation_policy.draft.json").read_text(
            encoding="utf-8"
        )
    )

    assert active["policy_id"] == "market-triggered-causal-discovery-v0"
    assert active["architecture"]["transcript_completeness_is_discovery_gate"] is False
    assert active["legacy_compatibility"]["frozen_v1"] == "frozen_audit_only"
    assert active["legacy_compatibility"]["quartr_availability_may_gate_active_architecture"] is False

    assert legacy["status"] == "superseded_historical_only"
    assert legacy["active_for_execution"] is False
    assert legacy["frozen_v1_rewritten"] is False
    assert legacy["superseded_by"] == active["policy_id"]


def test_current_roadmap_is_declared_source_of_truth() -> None:
    active = _active_policy()
    roadmap = REPO_ROOT / active["architecture_source_of_truth"]
    compatibility = REPO_ROOT / active["compatibility_map"]
    assert roadmap.exists()
    assert compatibility.exists()


def test_architecture_consolidation_is_complete_and_phase_one_is_next() -> None:
    active = _active_policy()
    assert active["architecture_consolidation_complete"] is True

    phases = {item["phase"]: item for item in active["development_phases"]}
    assert phases[0]["name"] == "architecture_consolidation"
    assert phases[0]["status"] == "complete"
    assert phases[1]["name"] == "real_market_trigger"
    assert phases[1]["status"] == "next"


def test_provider_and_validation_boundaries_are_machine_readable() -> None:
    active = _active_policy()
    boundaries = active["integration_boundaries"]
    assert boundaries["provider_specific_code_below_normalization"] is True
    assert boundaries["atomic_signal_remains_operating_signal_contract"] is True
    assert boundaries["new_operating_support_is_adapter_not_replacement_schema"] is True
    assert boundaries["new_end_to_end_replay_must_not_extend_frozen_validation_cli_family"] is True
    assert boundaries["physical_package_reorganization_before_interface_stability"] is False
