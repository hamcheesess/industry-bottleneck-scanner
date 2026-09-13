from datetime import datetime, timezone
from pathlib import Path

import pytest

from industry_bottleneck_scanner.causal_expansion import CausalEvidence
from industry_bottleneck_scanner.industry_state import (
    FileIndustryStateRegistry,
    IndustryStateSnapshot,
    snapshot_from_dict,
    snapshot_to_dict,
)


def dt(day: int) -> datetime:
    return datetime(2023, 1, day, tzinfo=timezone.utc)


def evidence(evidence_id: str, evidence_class: str, observed_at: datetime) -> CausalEvidence:
    return CausalEvidence(
        evidence_id=evidence_id,
        evidence_class=evidence_class,  # type: ignore[arg-type]
        source_id=f"source:{evidence_id}",
        observed_at=observed_at,
        summary=evidence_id,
    )


def constrained_snapshot(*, as_of: datetime) -> IndustryStateSnapshot:
    return IndustryStateSnapshot(
        node_id="large-power-transformers",
        as_of=as_of,
        supply_inelasticity=5,
        lead_time_pressure=5,
        capacity_tightness=4,
        capacity_expansion_difficulty=5,
        qualification_barrier=4,
        pricing_pressure=3,
        evidence=(
            evidence("lead-times", "lead_time_constraint", dt(1)),
            evidence("capacity", "supplier_capacity_expansion", dt(2)),
            evidence("industry", "physical_industry_data", dt(3)),
        ),
    )


def test_constrained_snapshot_is_classified_from_multiple_evidence_classes() -> None:
    snapshot = constrained_snapshot(as_of=dt(10))
    assert snapshot.constraint_score >= 80
    assert snapshot.stage == "severely_constrained"
    assert len(snapshot.independent_evidence_classes) == 3


def test_single_evidence_class_stays_unknown_even_with_high_scores() -> None:
    snapshot = IndustryStateSnapshot(
        node_id="opaque-node",
        as_of=dt(10),
        supply_inelasticity=5,
        lead_time_pressure=5,
        capacity_tightness=5,
        capacity_expansion_difficulty=5,
        qualification_barrier=5,
        pricing_pressure=5,
        evidence=(
            evidence("self-1", "management_operating_commentary", dt(1)),
            evidence("self-2", "management_operating_commentary", dt(2)),
        ),
    )
    assert snapshot.constraint_score == 100
    assert snapshot.stage == "unknown"


def test_industry_state_rejects_future_evidence() -> None:
    with pytest.raises(ValueError, match="look-ahead"):
        IndustryStateSnapshot(
            node_id="late-state",
            as_of=dt(5),
            supply_inelasticity=4,
            lead_time_pressure=4,
            capacity_tightness=4,
            capacity_expansion_difficulty=4,
            qualification_barrier=4,
            pricing_pressure=4,
            evidence=(evidence("future", "physical_industry_data", dt(6)),),
        )


def test_file_registry_preserves_history_and_returns_latest_strictly_pre_shock(tmp_path: Path) -> None:
    path = tmp_path / "industry-state.jsonl"
    registry = FileIndustryStateRegistry(path)
    early = constrained_snapshot(as_of=dt(10))
    later = IndustryStateSnapshot(
        node_id="large-power-transformers",
        as_of=dt(20),
        supply_inelasticity=4,
        lead_time_pressure=4,
        capacity_tightness=4,
        capacity_expansion_difficulty=4,
        qualification_barrier=4,
        pricing_pressure=4,
        evidence=(
            evidence("late-lead", "lead_time_constraint", dt(15)),
            evidence("late-capacity", "supplier_capacity_expansion", dt(16)),
        ),
    )
    registry.append(early)
    registry.append(later)

    assert registry.latest_before(node_id="large-power-transformers", cutoff=dt(20)) == early
    assert registry.latest_before(
        node_id="large-power-transformers", cutoff=dt(20), strict=False
    ) == later


def test_snapshot_round_trip_preserves_evidence_and_stage() -> None:
    snapshot = constrained_snapshot(as_of=dt(10))
    restored = snapshot_from_dict(snapshot_to_dict(snapshot))
    assert restored == snapshot
    assert restored.stage == snapshot.stage
