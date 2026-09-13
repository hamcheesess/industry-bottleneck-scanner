from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from industry_bottleneck_scanner.later_confirmation import (
    build_diagnostic,
    validate_plan,
)
from industry_bottleneck_scanner.later_confirmation_cli import main


ROOT = Path(__file__).resolve().parents[1]
COMMITTED_PLAN = (
    ROOT
    / "experiments"
    / "later_confirmation"
    / "large-power-transformers-2026-08-21.json"
)
AS_OF = "2026-08-21T23:59:59+00:00"


def replay_result() -> dict[str, object]:
    return {
        "schema_version": "historical-pre-news-replay-result-v1",
        "status": "full",
        "replay_id": "early-ai-electrical-2026-08-21-two-root-v2",
        "as_of": AS_OF,
        "rankings": [
            {
                "node_id": "large-power-transformers",
                "stage": "evidence_backed",
                "score": 73.0,
                "convergence_stage": "priority_convergence",
                "convergence_score": 75.07,
            }
        ],
    }


def plan() -> dict[str, object]:
    return json.loads(COMMITTED_PLAN.read_text(encoding="utf-8"))


def evidence_record(
    *,
    evidence_id: str,
    source_class: str,
    source_entity_id: str,
    direction: str = "confirming",
    observed_at: str = "2026-09-15T00:00:00+00:00",
) -> dict[str, object]:
    return {
        "slot_id": "lpt-demand-realization-90d",
        "evidence_id": evidence_id,
        "observed_at": observed_at,
        "source_id": f"https://example.test/{evidence_id}",
        "source_class": source_class,
        "source_entity_id": source_entity_id,
        "direction": direction,
        "fact": "독립된 1차 자료가 실제 송전 또는 변압기 주문 전환을 구체적으로 확인했다.",
    }


def test_committed_plan_freezes_four_required_slots_and_blocks_security_claim() -> None:
    normalized = validate_plan(plan(), replay_result())

    assert normalized["node_id"] == "large-power-transformers"
    assert normalized["replay_id"] == "early-ai-electrical-2026-08-21-two-root-v2"
    assert normalized["automatic_rerank"] is False
    assert normalized["security_level_conclusion"] is False
    slots = normalized["slots"]
    assert isinstance(slots, list)
    assert sum(item["required_for_node_validation"] is True for item in slots) == 4
    blocked = [item for item in slots if item["prerequisite_status"] == "blocked"]
    assert [item["thesis_dimension"] for item in blocked] == ["expectation_gap"]
    assert all(item["not_before"] > AS_OF for item in slots)


def test_empty_holdout_is_pending_and_preserves_original_replay() -> None:
    diagnostic = build_diagnostic(
        plan(),
        replay_result(),
        evaluation_as_of=datetime(2026, 8, 29, tzinfo=timezone.utc),
    )

    assert diagnostic["node_diagnostic_status"] == "pending"
    assert diagnostic["security_thesis_readiness"] == "not_decision_grade"
    assert diagnostic["automatic_rerank"] is False
    assert diagnostic["original_replay_unchanged"] is True
    assert diagnostic["original_ranking"] == {
        "stage": "evidence_backed",
        "score": 73.0,
        "convergence_stage": "priority_convergence",
        "convergence_score": 75.07,
    }
    statuses = {item["slot_id"]: item["status"] for item in diagnostic["slot_results"]}
    assert statuses["lpt-expectation-gap-security"] == "blocked"
    assert set(statuses.values()) == {"pending", "blocked"}


def test_plan_rejects_holdout_window_at_replay_cutoff() -> None:
    invalid = plan()
    invalid["slots"][0]["not_before"] = AS_OF

    with pytest.raises(ValueError, match="strictly after"):
        validate_plan(invalid, replay_result())


@pytest.mark.parametrize(
    "observed_at,error",
    [
        (AS_OF, "strictly after"),
        ("2026-11-20T00:00:00+00:00", "after its frozen window"),
    ],
)
def test_evidence_cannot_leak_across_frozen_window(observed_at: str, error: str) -> None:
    package = {
        "schema_version": "later-confirmation-evidence-v1",
        "plan_id": "large-power-transformers-2026-08-21-v1",
        "records": [
            evidence_record(
                evidence_id="one",
                source_class="issuer_operating_disclosure",
                source_entity_id="issuer-one",
                observed_at=observed_at,
            )
        ],
    }

    with pytest.raises(ValueError, match=error):
        build_diagnostic(
            plan(),
            replay_result(),
            evaluation_as_of=datetime(2027, 1, 1, tzinfo=timezone.utc),
            evidence_package=package,
        )


def test_independent_confirmations_complete_one_slot_without_confirming_node() -> None:
    package = {
        "schema_version": "later-confirmation-evidence-v1",
        "plan_id": "large-power-transformers-2026-08-21-v1",
        "records": [
            evidence_record(
                evidence_id="issuer-order",
                source_class="issuer_operating_disclosure",
                source_entity_id="issuer-one",
            ),
            evidence_record(
                evidence_id="regulatory-project",
                source_class="regulatory_record",
                source_entity_id="regulator-one",
            ),
        ],
    }
    diagnostic = build_diagnostic(
        plan(),
        replay_result(),
        evaluation_as_of=datetime(2026, 10, 1, tzinfo=timezone.utc),
        evidence_package=package,
    )

    demand = next(
        item
        for item in diagnostic["slot_results"]
        if item["slot_id"] == "lpt-demand-realization-90d"
    )
    assert demand["status"] == "confirmed"
    assert diagnostic["node_diagnostic_status"] == "pending"


def test_diverse_opposing_evidence_is_mixed() -> None:
    package = {
        "schema_version": "later-confirmation-evidence-v1",
        "plan_id": "large-power-transformers-2026-08-21-v1",
        "records": [
            evidence_record(
                evidence_id="issuer-order",
                source_class="issuer_operating_disclosure",
                source_entity_id="issuer-one",
            ),
            evidence_record(
                evidence_id="regulatory-cancellation",
                source_class="regulatory_record",
                source_entity_id="regulator-one",
                direction="disconfirming",
            ),
        ],
    }
    diagnostic = build_diagnostic(
        plan(),
        replay_result(),
        evaluation_as_of=datetime(2026, 10, 1, tzinfo=timezone.utc),
        evidence_package=package,
    )

    demand = next(
        item
        for item in diagnostic["slot_results"]
        if item["slot_id"] == "lpt-demand-realization-90d"
    )
    assert demand["status"] == "mixed"
    assert diagnostic["node_diagnostic_status"] == "mixed"


def test_cli_writes_reader_facing_korean_holdout(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    replay_path = tmp_path / "replay.json"
    plan_path.write_text(json.dumps(plan(), ensure_ascii=False), encoding="utf-8")
    replay_path.write_text(json.dumps(replay_result()), encoding="utf-8")

    assert (
        main(
            [
                "--plan",
                str(plan_path),
                "--replay-result",
                str(replay_path),
                "--evaluation-as-of",
                "2026-08-29T23:59:59+00:00",
                "--output-dir",
                str(tmp_path / "output"),
            ]
        )
        == 0
    )
    diagnostic = json.loads(
        (tmp_path / "output" / "later_confirmation_diagnostic.json").read_text()
    )
    rendered = (tmp_path / "output" / "later_confirmation.ko.md").read_text()
    assert diagnostic["original_replay_unchanged"] is True
    assert "사전에 고정한 판정 기준" in rendered
    assert "왜" not in rendered or "확인" in rendered
    assert "원 replay 점수·단계는 변경하지 않음" in rendered
    assert "증권 명제 준비도" in rendered
