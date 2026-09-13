from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from industry_bottleneck_scanner.causal_expansion import CausalEvidence
from industry_bottleneck_scanner.industry_state import FileIndustryStateRegistry
from industry_bottleneck_scanner.industry_state_updater import (
    IndustryStateObservation,
    evaluate_industry_state_update,
    observation_from_atomic_signal,
    observations_from_atomic_signals,
    update_industry_state_registry,
)
from industry_bottleneck_scanner.models import AtomicSignal, Classification


AS_OF = datetime(2026, 8, 21, 20, 0, tzinfo=timezone.utc)
NODE = "large-power-transformers"


def signal(
    signal_id: str,
    metric: str,
    *,
    company_id: str = "issuer-a",
    direction: str = "strengthening",
    negated: bool = False,
) -> AtomicSignal:
    return AtomicSignal(
        signal_id=signal_id,
        scanner="scarcity" if metric != "pricing_power" else "pricing",
        metric=metric,
        direction=direction,  # type: ignore[arg-type]
        magnitude="unknown",
        company_id=company_id,
        ticker=company_id.upper(),
        classification=Classification(industry="Electrical Equipment"),
        subject=None,
        document_id=f"document-{signal_id}",
        document_type="sec_10q",
        published_at=AS_OF - timedelta(days=5),
        source_url="https://www.sec.gov/example",
        evidence_text=f"evidence for {metric}",
        negated=negated,
        resolved=False,
        extraction_method="keyword",
        confidence=0.9,
    )


def observation(
    observation_id: str,
    dimension: str,
    score: int,
    evidence_class: str,
    *,
    source_id: str | None = None,
    observed_at: datetime | None = None,
    source_company_id: str | None = None,
) -> IndustryStateObservation:
    timestamp = observed_at or AS_OF - timedelta(days=1)
    return IndustryStateObservation(
        observation_id=observation_id,
        node_id=NODE,
        dimension=dimension,  # type: ignore[arg-type]
        score=score,
        observed_at=timestamp,
        evidence=CausalEvidence(
            evidence_id=f"evidence-{observation_id}",
            evidence_class=evidence_class,  # type: ignore[arg-type]
            source_id=source_id or f"source-{observation_id}",
            observed_at=timestamp,
            summary=observation_id,
            source_company_id=source_company_id,
        ),
    )


def test_atomic_signal_mapping_requires_explicit_economic_node() -> None:
    mapped = observation_from_atomic_signal(signal("lead", "lead_time_pressure"), node_id=NODE)
    unsupported = observation_from_atomic_signal(signal("orders", "backlog_strength"), node_id=NODE)
    negated = observation_from_atomic_signal(
        signal("negated", "capacity_constraint", negated=True),
        node_id=NODE,
    )

    assert mapped is not None
    assert mapped.node_id == NODE
    assert mapped.dimension == "lead_time_pressure"
    assert mapped.score == 4
    assert mapped.evidence.evidence_class == "lead_time_constraint"
    assert unsupported is None
    assert negated is None


def test_company_to_node_assignment_is_many_to_many_and_not_classification_driven() -> None:
    observations = observations_from_atomic_signals(
        (signal("capacity", "capacity_constraint"),),
        company_node_assignments={"issuer-a": (NODE, "distribution-transformers")},
    )

    assert [item.node_id for item in observations] == [
        "distribution-transformers",
        NODE,
    ]


def test_update_fails_closed_without_evidence_and_source_diversity(tmp_path: Path) -> None:
    registry = FileIndustryStateRegistry(tmp_path / "state.jsonl")
    decision = update_industry_state_registry(
        registry,
        node_id=NODE,
        as_of=AS_OF,
        observations=(
            observation(
                "one",
                "capacity_tightness",
                5,
                "capacity_utilization",
                source_id="same-source",
            ),
            observation(
                "two",
                "lead_time_pressure",
                5,
                "capacity_utilization",
                source_id="same-source",
            ),
        ),
    )

    assert decision.approved is False
    assert "insufficient_independent_evidence_classes" in decision.reasons
    assert "insufficient_independent_sources" in decision.reasons
    assert registry.load() == ()


def test_multiple_documents_from_one_issuer_do_not_count_as_independent_sources() -> None:
    decision = evaluate_industry_state_update(
        node_id=NODE,
        as_of=AS_OF,
        observations=(
            observation(
                "issuer-lead",
                "lead_time_pressure",
                5,
                "lead_time_constraint",
                source_company_id="same-issuer",
            ),
            observation(
                "issuer-capacity",
                "capacity_tightness",
                5,
                "capacity_utilization",
                source_company_id="same-issuer",
            ),
        ),
    )

    assert decision.independent_evidence_classes == (
        "capacity_utilization",
        "lead_time_constraint",
    )
    assert decision.independent_source_entities == ("company:same-issuer",)
    assert decision.approved is False
    assert "insufficient_independent_sources" in decision.reasons


def test_approved_update_is_appended_and_unobserved_dimensions_carry_forward(tmp_path: Path) -> None:
    registry = FileIndustryStateRegistry(tmp_path / "state.jsonl")
    first = update_industry_state_registry(
        registry,
        node_id=NODE,
        as_of=AS_OF,
        observations=(
            observation("lead", "lead_time_pressure", 5, "lead_time_constraint"),
            observation("capacity", "capacity_tightness", 4, "capacity_utilization"),
            observation("supply", "supply_inelasticity", 5, "physical_industry_data"),
            observation("qualification", "qualification_barrier", 4, "qualification_barrier"),
            observation("pricing", "pricing_pressure", 4, "pricing_or_repricing"),
        ),
    )
    assert first.approved is True
    assert first.snapshot.stage == "constrained"

    later_as_of = AS_OF + timedelta(days=30)
    second = update_industry_state_registry(
        registry,
        node_id=NODE,
        as_of=later_as_of,
        observations=(
            observation(
                "pricing-later",
                "pricing_pressure",
                5,
                "pricing_or_repricing",
                observed_at=later_as_of - timedelta(days=1),
            ),
        ),
    )

    assert second.approved is True
    assert second.snapshot.lead_time_pressure == 5
    assert second.snapshot.capacity_tightness == 4
    assert second.snapshot.pricing_pressure == 5
    assert second.previous_as_of == AS_OF
    assert len(registry.load()) == 2


def test_future_observation_and_duplicate_snapshot_timestamp_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="look-ahead"):
        evaluate_industry_state_update(
            node_id=NODE,
            as_of=AS_OF,
            observations=(
                observation(
                    "future",
                    "capacity_tightness",
                    5,
                    "capacity_utilization",
                    observed_at=AS_OF + timedelta(seconds=1),
                ),
            ),
        )

    registry = FileIndustryStateRegistry(tmp_path / "state.jsonl")
    accepted = (
        observation("one", "lead_time_pressure", 5, "lead_time_constraint"),
        observation("two", "capacity_tightness", 5, "capacity_utilization"),
    )
    assert update_industry_state_registry(
        registry,
        node_id=NODE,
        as_of=AS_OF,
        observations=accepted,
    ).approved
    with pytest.raises(ValueError, match="already exists"):
        update_industry_state_registry(
            registry,
            node_id=NODE,
            as_of=AS_OF,
            observations=accepted,
        )
