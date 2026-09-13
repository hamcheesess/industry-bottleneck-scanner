from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from industry_bottleneck_scanner.artifacts import atomic_signal_payload
from industry_bottleneck_scanner.causal_expansion import CausalEvidence
from industry_bottleneck_scanner.industry_state import FileIndustryStateRegistry
from industry_bottleneck_scanner.industry_state_update_cli import main
from industry_bottleneck_scanner.industry_state_updater import (
    IndustryStateObservation,
    observation_to_dict,
)
from industry_bottleneck_scanner.models import AtomicSignal, Classification


AS_OF = datetime(2026, 8, 21, 20, 0, tzinfo=timezone.utc)
NODE = "large-power-transformers"
REPO_ROOT = Path(__file__).resolve().parents[1]


def observation(name: str, dimension: str, evidence_class: str) -> IndustryStateObservation:
    observed_at = AS_OF - timedelta(days=1)
    return IndustryStateObservation(
        observation_id=name,
        node_id=NODE,
        dimension=dimension,  # type: ignore[arg-type]
        score=5,
        observed_at=observed_at,
        evidence=CausalEvidence(
            evidence_id=f"evidence-{name}",
            evidence_class=evidence_class,  # type: ignore[arg-type]
            source_id=f"source-{name}",
            observed_at=observed_at,
            summary=name,
        ),
    )


def write_jsonl(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def base_args(tmp_path: Path) -> list[str]:
    return [
        "--as-of",
        AS_OF.isoformat(),
        "--registry",
        str(tmp_path / "industry-state.jsonl"),
        "--decisions",
        str(tmp_path / "decisions.json"),
    ]


def test_cli_appends_only_evidence_diverse_observation_batch(tmp_path: Path) -> None:
    observations = tmp_path / "observations.jsonl"
    write_jsonl(
        observations,
        (
            observation_to_dict(observation("lead", "lead_time_pressure", "lead_time_constraint")),
            observation_to_dict(observation("capacity", "capacity_tightness", "capacity_utilization")),
        ),
    )

    assert main(["--observations-jsonl", str(observations), *base_args(tmp_path)]) == 0

    registry = FileIndustryStateRegistry(tmp_path / "industry-state.jsonl")
    payload = json.loads((tmp_path / "decisions.json").read_text(encoding="utf-8"))
    assert len(registry.load()) == 1
    assert payload["approved_count"] == 1
    assert payload["decisions"][0]["snapshot"]["node_id"] == NODE


def test_cli_derives_observations_from_atomic_signals_only_after_node_assignment(
    tmp_path: Path,
) -> None:
    signals = tmp_path / "atomic-signals.jsonl"
    assignments = tmp_path / "assignments.csv"
    published_at = AS_OF - timedelta(days=3)
    items = (
        AtomicSignal(
            signal_id="lead",
            scanner="scarcity",
            metric="lead_time_pressure",
            direction="strengthening",
            magnitude="unknown",
            company_id="issuer-a",
            ticker="AAA",
            classification=Classification(industry="Electrical Equipment"),
            subject=None,
            document_id="document-a",
            document_type="sec_10q",
            published_at=published_at,
            source_url="https://www.sec.gov/a",
            evidence_text="Long lead times remain elevated.",
            negated=False,
            resolved=False,
            extraction_method="keyword",
            confidence=0.9,
        ),
        AtomicSignal(
            signal_id="capacity",
            scanner="scarcity",
            metric="capacity_constraint",
            direction="strengthening",
            magnitude="unknown",
            company_id="issuer-b",
            ticker="BBB",
            classification=Classification(industry="Electrical Equipment"),
            subject=None,
            document_id="document-b",
            document_type="sec_8k_exhibit",
            published_at=published_at,
            source_url="https://www.sec.gov/b",
            evidence_text="Capacity remains constrained.",
            negated=False,
            resolved=False,
            extraction_method="keyword",
            confidence=0.9,
        ),
    )
    write_jsonl(signals, tuple(atomic_signal_payload(item) for item in items))
    assignments.write_text(
        f"company_id,node_id\nissuer-a,{NODE}\nissuer-b,{NODE}\n",
        encoding="utf-8",
    )

    assert main(
        [
            "--atomic-signals-jsonl",
            str(signals),
            "--node-assignments-csv",
            str(assignments),
            *base_args(tmp_path),
        ]
    ) == 0

    snapshot = FileIndustryStateRegistry(tmp_path / "industry-state.jsonl").load()[0]
    assert snapshot.lead_time_pressure == 4
    assert snapshot.capacity_tightness == 4
    assert snapshot.independent_evidence_classes == (
        "capacity_utilization",
        "lead_time_constraint",
    )


def test_curated_grid_state_is_strictly_pre_trigger_and_source_diverse(tmp_path: Path) -> None:
    observations = (
        REPO_ROOT
        / "experiments"
        / "industry_state"
        / "large-load-grid-interconnection-capacity.jsonl"
    )
    registry = tmp_path / "industry-state.jsonl"
    decisions = tmp_path / "decisions.json"
    state_as_of = "2026-08-20T23:59:59+00:00"

    assert main(
        [
            "--observations-jsonl",
            str(observations),
            "--as-of",
            state_as_of,
            "--registry",
            str(registry),
            "--decisions",
            str(decisions),
        ]
    ) == 0

    payload = json.loads(decisions.read_text(encoding="utf-8"))
    snapshot = FileIndustryStateRegistry(registry).load()[0]
    assert payload["approved_count"] == 1
    assert snapshot.node_id == "large-load-grid-interconnection-capacity"
    assert snapshot.as_of < datetime(2026, 8, 21, tzinfo=timezone.utc)
    assert snapshot.stage == "tightening"
    assert snapshot.constraint_score == 61.0
    assert snapshot.supply_inelasticity == 3
    assert snapshot.capacity_tightness == 4
    assert snapshot.capacity_expansion_difficulty == 4
    assert len({item.source_id for item in snapshot.evidence}) == 2
    assert all(item.observed_at <= snapshot.as_of for item in snapshot.evidence)


def test_curated_transformer_state_is_pre_trigger_and_severely_constrained(
    tmp_path: Path,
) -> None:
    observations = (
        REPO_ROOT
        / "experiments"
        / "industry_state"
        / "large-power-transformers.jsonl"
    )
    registry = tmp_path / "industry-state.jsonl"
    decisions = tmp_path / "decisions.json"
    state_as_of = "2026-08-20T23:59:59+00:00"

    assert main(
        [
            "--observations-jsonl",
            str(observations),
            "--as-of",
            state_as_of,
            "--registry",
            str(registry),
            "--decisions",
            str(decisions),
        ]
    ) == 0

    payload = json.loads(decisions.read_text(encoding="utf-8"))
    decision = payload["decisions"][0]
    snapshot = FileIndustryStateRegistry(registry).load()[0]
    assert payload["approved_count"] == 1
    assert snapshot.node_id == "large-power-transformers"
    assert snapshot.as_of < datetime(2026, 8, 21, tzinfo=timezone.utc)
    assert snapshot.stage == "severely_constrained"
    assert snapshot.constraint_score == 84.0
    assert snapshot.lead_time_pressure == 5
    assert snapshot.capacity_tightness == 4
    assert snapshot.capacity_expansion_difficulty == 5
    assert len(decision["independent_evidence_classes"]) == 5
    assert len(decision["independent_source_entities"]) == 3
    assert all(item.observed_at <= snapshot.as_of for item in snapshot.evidence)


def test_industry_state_workflow_requires_approved_strict_pre_trigger_node() -> None:
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "industry-state-adjudication.yml"
    ).read_text(encoding="utf-8")

    assert "approved_count" in workflow
    assert "cutoff >= trigger" in workflow
    assert "ibs-industry-state-update" in workflow
    assert "observations_path must stay inside" in workflow
    assert "continue-on-error" not in workflow
