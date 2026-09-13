from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path


PLAN_SCHEMA = "later-confirmation-plan-v1"
EVIDENCE_SCHEMA = "later-confirmation-evidence-v1"
DIAGNOSTIC_SCHEMA = "later-confirmation-diagnostic-v1"
REPLAY_RESULT_SCHEMA = "historical-pre-news-replay-result-v1"

ALLOWED_DIMENSIONS = {
    "demand_realization",
    "bottleneck_persistence",
    "supply_response",
    "economic_capture",
    "expectation_gap",
}
ALLOWED_DIRECTIONS = {"confirming", "disconfirming", "mixed"}
ALLOWED_PREREQUISITES = {"open", "blocked"}


def _required_text(payload: dict[str, object], key: str, *, minimum: int = 1) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise ValueError(f"{key} must be text with at least {minimum} characters")
    return value.strip()


def _aware(value: object, name: str) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return parsed


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _string_list(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    result = [str(item).strip() for item in value]
    if any(not item for item in result) or len(set(result)) != len(result):
        raise ValueError(f"{name} must contain unique non-empty strings")
    return result


def canonical_sha256(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_plan(
    plan: dict[str, object], replay_result: dict[str, object]
) -> dict[str, object]:
    if plan.get("schema_version") != PLAN_SCHEMA:
        raise ValueError("unsupported later-confirmation plan schema")
    if replay_result.get("schema_version") != REPLAY_RESULT_SCHEMA:
        raise ValueError("unsupported replay-result schema")
    if replay_result.get("status") != "full":
        raise ValueError("later-confirmation plan requires a full replay result")

    plan_id = _required_text(plan, "plan_id")
    replay_id = _required_text(plan, "replay_id")
    node_id = _required_text(plan, "node_id")
    if replay_result.get("replay_id") != replay_id:
        raise ValueError("later-confirmation replay_id does not match replay result")
    replay_as_of = _aware(plan.get("replay_as_of"), "replay_as_of")
    result_as_of = _aware(replay_result.get("as_of"), "replay result as_of")
    if replay_as_of != result_as_of:
        raise ValueError("later-confirmation replay_as_of must match replay result")
    frozen_at = _aware(plan.get("frozen_at"), "frozen_at")
    if frozen_at <= replay_as_of:
        raise ValueError("later-confirmation plan must be frozen after replay_as_of")
    if plan.get("automatic_rerank") is not False:
        raise ValueError("later-confirmation evidence must not automatically rerank the replay")
    if plan.get("security_level_conclusion") is not False:
        raise ValueError("later-confirmation plan must not contain a security conclusion")

    rankings = replay_result.get("rankings")
    if not isinstance(rankings, list):
        raise ValueError("replay rankings must be a list")
    matching = [item for item in rankings if isinstance(item, dict) and item.get("node_id") == node_id]
    if len(matching) != 1:
        raise ValueError("later-confirmation node must match exactly one replay ranking")

    raw_slots = plan.get("slots")
    if not isinstance(raw_slots, list) or not raw_slots:
        raise ValueError("later-confirmation plan requires slots")
    slots: list[dict[str, object]] = []
    slot_ids: set[str] = set()
    for index, raw in enumerate(raw_slots):
        if not isinstance(raw, dict):
            raise ValueError(f"slots[{index}] must be an object")
        slot_id = _required_text(raw, "slot_id")
        if slot_id in slot_ids:
            raise ValueError("later-confirmation slot_id values must be unique")
        slot_ids.add(slot_id)
        dimension = _required_text(raw, "thesis_dimension")
        if dimension not in ALLOWED_DIMENSIONS:
            raise ValueError(f"unsupported holdout thesis_dimension: {dimension}")
        not_before = _aware(raw.get("not_before"), f"slots[{index}].not_before")
        due_by = _aware(raw.get("due_by"), f"slots[{index}].due_by")
        if not_before <= replay_as_of:
            raise ValueError("holdout windows must begin strictly after replay_as_of")
        if due_by < not_before:
            raise ValueError("holdout due_by must not precede not_before")
        prerequisite = _required_text(raw, "prerequisite_status")
        if prerequisite not in ALLOWED_PREREQUISITES:
            raise ValueError("unsupported holdout prerequisite_status")
        required_for_node = raw.get("required_for_node_validation")
        if not isinstance(required_for_node, bool):
            raise ValueError("required_for_node_validation must be boolean")
        blocking_reason = str(raw.get("blocking_reason", "")).strip()
        if prerequisite == "blocked" and (required_for_node or not blocking_reason):
            raise ValueError("blocked slots must be non-required and state a blocking reason")
        allowed_sources = _string_list(
            raw.get("allowed_source_classes"),
            f"slots[{index}].allowed_source_classes",
        )
        minimum_entity_count = _positive_int(
            raw.get("minimum_entity_count"), f"slots[{index}].minimum_entity_count"
        )
        minimum_source_class_count = _positive_int(
            raw.get("minimum_source_class_count"),
            f"slots[{index}].minimum_source_class_count",
        )
        if minimum_source_class_count > len(allowed_sources):
            raise ValueError("minimum_source_class_count exceeds allowed source classes")
        slots.append(
            {
                "slot_id": slot_id,
                "label": _required_text(raw, "label"),
                "thesis_dimension": dimension,
                "question": _required_text(raw, "question", minimum=20),
                "not_before": not_before.isoformat(),
                "due_by": due_by.isoformat(),
                "allowed_source_classes": allowed_sources,
                "minimum_entity_count": minimum_entity_count,
                "minimum_source_class_count": minimum_source_class_count,
                "confirm_definition": _required_text(raw, "confirm_definition", minimum=20),
                "warning_definition": _required_text(raw, "warning_definition", minimum=20),
                "break_definition": _required_text(raw, "break_definition", minimum=20),
                "required_for_node_validation": required_for_node,
                "prerequisite_status": prerequisite,
                "blocking_reason": blocking_reason,
            }
        )

    normalized = {
        "schema_version": PLAN_SCHEMA,
        "plan_id": plan_id,
        "replay_id": replay_id,
        "node_id": node_id,
        "replay_as_of": replay_as_of.isoformat(),
        "frozen_at": frozen_at.isoformat(),
        "automatic_rerank": False,
        "security_level_conclusion": False,
        "slots": slots,
    }
    normalized["plan_sha256"] = canonical_sha256(normalized)
    return normalized


def build_diagnostic(
    plan: dict[str, object],
    replay_result: dict[str, object],
    *,
    evaluation_as_of: datetime,
    evidence_package: dict[str, object] | None = None,
) -> dict[str, object]:
    if evaluation_as_of.tzinfo is None or evaluation_as_of.utcoffset() is None:
        raise ValueError("evaluation_as_of must be timezone-aware")
    normalized = validate_plan(plan, replay_result)
    replay_as_of = _aware(normalized["replay_as_of"], "replay_as_of")
    if evaluation_as_of <= replay_as_of:
        raise ValueError("evaluation_as_of must be after replay_as_of")

    records_by_slot: dict[str, list[dict[str, object]]] = {
        str(slot["slot_id"]): [] for slot in normalized["slots"]  # type: ignore[index]
    }
    slots_by_id = {
        str(slot["slot_id"]): slot for slot in normalized["slots"]  # type: ignore[index]
    }
    seen_evidence: set[str] = set()
    if evidence_package is not None:
        if evidence_package.get("schema_version") != EVIDENCE_SCHEMA:
            raise ValueError("unsupported later-confirmation evidence schema")
        if evidence_package.get("plan_id") != normalized["plan_id"]:
            raise ValueError("later-confirmation evidence plan_id mismatch")
        raw_records = evidence_package.get("records")
        if not isinstance(raw_records, list):
            raise ValueError("later-confirmation records must be a list")
        for index, raw in enumerate(raw_records):
            if not isinstance(raw, dict):
                raise ValueError(f"records[{index}] must be an object")
            slot_id = _required_text(raw, "slot_id")
            slot = slots_by_id.get(slot_id)
            if slot is None:
                raise ValueError(f"unknown later-confirmation slot_id: {slot_id}")
            if slot["prerequisite_status"] == "blocked":
                raise ValueError("evidence cannot be appended to a blocked holdout slot")
            evidence_id = _required_text(raw, "evidence_id")
            if evidence_id in seen_evidence:
                raise ValueError("later-confirmation evidence_id values must be unique")
            seen_evidence.add(evidence_id)
            observed_at = _aware(raw.get("observed_at"), f"records[{index}].observed_at")
            if observed_at <= replay_as_of:
                raise ValueError("holdout evidence must be strictly after replay_as_of")
            if observed_at > evaluation_as_of:
                raise ValueError("holdout evidence cannot exceed evaluation_as_of")
            if observed_at < _aware(slot["not_before"], "slot not_before"):
                raise ValueError("holdout evidence precedes its frozen window")
            if observed_at > _aware(slot["due_by"], "slot due_by"):
                raise ValueError("holdout evidence falls after its frozen window")
            source_class = _required_text(raw, "source_class")
            if source_class not in slot["allowed_source_classes"]:
                raise ValueError("holdout evidence uses a non-frozen source class")
            direction = _required_text(raw, "direction")
            if direction not in ALLOWED_DIRECTIONS:
                raise ValueError("unsupported holdout evidence direction")
            records_by_slot[slot_id].append(
                {
                    "evidence_id": evidence_id,
                    "observed_at": observed_at.isoformat(),
                    "source_id": _required_text(raw, "source_id"),
                    "source_class": source_class,
                    "source_entity_id": _required_text(raw, "source_entity_id"),
                    "direction": direction,
                    "fact": _required_text(raw, "fact", minimum=20),
                }
            )

    slot_results: list[dict[str, object]] = []
    for slot in normalized["slots"]:  # type: ignore[index]
        slot_id = str(slot["slot_id"])
        records = records_by_slot[slot_id]
        entities = {str(item["source_entity_id"]) for item in records}
        source_classes = {str(item["source_class"]) for item in records}
        if slot["prerequisite_status"] == "blocked":
            status = "blocked"
        elif not records:
            status = "pending"
        elif (
            len(entities) < slot["minimum_entity_count"]
            or len(source_classes) < slot["minimum_source_class_count"]
        ):
            status = "partial"
        else:
            directions = {str(item["direction"]) for item in records}
            if directions == {"confirming"}:
                status = "confirmed"
            elif directions == {"disconfirming"}:
                status = "disconfirmed"
            else:
                status = "mixed"
        slot_results.append(
            {
                **slot,
                "status": status,
                "evidence_count": len(records),
                "source_entity_count": len(entities),
                "source_class_count": len(source_classes),
                "records": sorted(records, key=lambda item: (item["observed_at"], item["evidence_id"])),
            }
        )

    required_statuses = [
        str(item["status"])
        for item in slot_results
        if item["required_for_node_validation"] is True
    ]
    if "disconfirmed" in required_statuses:
        node_diagnostic_status = "weakening"
    elif "mixed" in required_statuses:
        node_diagnostic_status = "mixed"
    elif required_statuses and all(item == "confirmed" for item in required_statuses):
        node_diagnostic_status = "confirmed"
    else:
        node_diagnostic_status = "pending"

    ranking = next(
        item
        for item in replay_result["rankings"]  # type: ignore[index]
        if isinstance(item, dict) and item.get("node_id") == normalized["node_id"]
    )
    diagnostic: dict[str, object] = {
        "schema_version": DIAGNOSTIC_SCHEMA,
        "plan_id": normalized["plan_id"],
        "plan_sha256": normalized["plan_sha256"],
        "replay_id": normalized["replay_id"],
        "node_id": normalized["node_id"],
        "replay_as_of": normalized["replay_as_of"],
        "evaluation_as_of": evaluation_as_of.isoformat(),
        "node_diagnostic_status": node_diagnostic_status,
        "security_thesis_readiness": "not_decision_grade",
        "automatic_rerank": False,
        "original_replay_unchanged": True,
        "original_ranking": {
            "stage": ranking.get("stage"),
            "score": ranking.get("score"),
            "convergence_stage": ranking.get("convergence_stage"),
            "convergence_score": ranking.get("convergence_score"),
        },
        "slot_results": slot_results,
    }
    diagnostic["diagnostic_sha256"] = canonical_sha256(diagnostic)
    return diagnostic


def render_diagnostic_markdown(diagnostic: dict[str, object]) -> str:
    lines = [
        "# 산업 병목 later-confirmation holdout",
        "",
        f"- 산업 노드: `{diagnostic['node_id']}`",
        f"- 원 replay: `{diagnostic['replay_id']}` / 기준시점 `{diagnostic['replay_as_of']}`",
        f"- 진단 기준시점: `{diagnostic['evaluation_as_of']}`",
        f"- 산업 노드 사후 진단: `{diagnostic['node_diagnostic_status']}`",
        f"- 증권 명제 준비도: `{diagnostic['security_thesis_readiness']}`",
        "- 원 replay 점수·단계는 변경하지 않음: `true`",
        "",
        "이 문서는 사후 자료로 과거 판단을 다시 쓰지 않습니다. 아래 질문·기간·출처 다양성은 결과를 확인하기 전에 봉인되며, 새 자료는 원 점수를 올리는 입력이 아니라 별도 확인 또는 반증 기록으로만 추가됩니다.",
        "",
        "| 확인 항목 | 기간 | 최소 독립성 | 현재 상태 | 산업 판단 질문 |",
        "|---|---|---:|---|---|",
    ]
    for item in diagnostic["slot_results"]:  # type: ignore[index]
        if not isinstance(item, dict):
            raise ValueError("invalid normalized slot result")
        question = str(item["question"]).replace("|", "\\|")
        lines.append(
            f"| {item['label']} | `{item['not_before']}` ~ `{item['due_by']}` | "
            f"기관 {item['minimum_entity_count']} / 출처유형 {item['minimum_source_class_count']} | "
            f"`{item['status']}` | {question} |"
        )
    lines.extend(["", "## 사전에 고정한 판정 기준", ""])
    for item in diagnostic["slot_results"]:  # type: ignore[index]
        if not isinstance(item, dict):
            raise ValueError("invalid normalized slot result")
        lines.extend(
            [
                f"### {item['label']}",
                "",
                f"- 확인: {item['confirm_definition']}",
                f"- 경고: {item['warning_definition']}",
                f"- 반증: {item['break_definition']}",
                f"- 허용 출처: {', '.join(str(value) for value in item['allowed_source_classes'])}",
            ]
        )
        if item["prerequisite_status"] == "blocked":
            lines.append(f"- 차단 사유: {item['blocking_reason']}")
        lines.append("")
    lines.extend(
        [
            "## 해석 경계",
            "",
            "- `pending`은 실패가 아니라 아직 고정 관측창과 독립성 요건이 채워지지 않았다는 뜻입니다.",
            "- 산업 명제 확인과 특정 상장사의 경제적 수익 포착은 별개입니다.",
            "- cutoff 당시 변압기 증권 바스켓과 기대치가 봉인되지 않았으므로 기대 차이·매수 판단은 사후 자료로 복원하지 않습니다.",
            "- 회사 노출 매핑은 별도 pre-cutoff 근거 계약을 통과해야 하며 이 holdout이 자동 승인하지 않습니다.",
            "",
            f"Plan SHA-256: `{diagnostic['plan_sha256']}`",
            f"Diagnostic SHA-256: `{diagnostic['diagnostic_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_diagnostic_artifacts(
    output_dir: Path, diagnostic: dict[str, object]
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "later_confirmation_diagnostic.json"
    markdown_path = output_dir / "later_confirmation.ko.md"
    payloads = (
        (json_path, json.dumps(diagnostic, indent=2, sort_keys=True, ensure_ascii=False) + "\n"),
        (markdown_path, render_diagnostic_markdown(diagnostic)),
    )
    for path, content in payloads:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    return json_path, markdown_path
