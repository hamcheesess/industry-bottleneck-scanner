from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path


WEEKLY_RESEARCH_INPUT_SCHEMA = "weekly-industry-research-input-v1"
WEEKLY_SITE_EXPORT_SCHEMA = "weekly-industry-research-site-export-v1"
TOKEN_FEEDBACK_SCHEMA = "report-token-efficiency-feedback-v1"

STAGES = (
    "market_screen",
    "persistence",
    "operating_evidence",
    "causal_validation",
    "bottleneck_quantification",
    "issuer_exposure",
    "financial_translation",
    "expectations_gap",
    "final_report",
)
STATUSES = {"active_research", "rejected", "final_report_published"}

SOURCE_CLASSES = {
    "issuer_primary",
    "customer_supplier_competitor",
    "government_regulator",
    "industry_technical",
    "market_expectations",
    "physical_market_data",
}
INDEPENDENT_SOURCE_CLASSES = SOURCE_CLASSES - {"issuer_primary"}

V1_RESEARCH_POLICY = {
    "cadence": "weekly",
    "quality_before_token_efficiency": True,
    "gpt_required_work": [
        "diverse_source_discovery",
        "causal_interpretation",
        "scenario_assumption_review",
        "variant_perception_review",
        "final_korean_synthesis",
    ],
    "code_first_work": [
        "collection",
        "normalization",
        "deduplication",
        "market_screening",
        "deterministic_financial_math",
        "compact_rejection_publication",
    ],
    "final_report_min_source_classes": 4,
    "final_report_min_independent_sources": 2,
    "report_generation": "finalists_only",
    "database_report_storage": "final_reports_only",
}


def _required_text(payload: dict[str, object], key: str, *, minimum: int = 1) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise ValueError(f"{key} must be text with at least {minimum} characters")
    return value.strip()


def _aware_datetime(value: object, name: str) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return parsed


def _nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _number(value: object, name: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if result < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return result


def _string_list(value: object, name: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{name} must be a list of non-empty strings")
    result = [item.strip() for item in value]
    if not allow_empty and not result:
        raise ValueError(f"{name} must not be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} must contain unique values")
    return result


def _canonical_sha256(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_source_classes(value: object, name: str) -> list[str]:
    source_classes = _string_list(value, name, allow_empty=False)
    unknown = sorted(set(source_classes) - SOURCE_CLASSES)
    if unknown:
        raise ValueError(f"{name} has unsupported values: {','.join(unknown)}")
    return source_classes


def _normalize_candidate(raw: object, *, run_as_of: datetime) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise ValueError("candidate must be an object")
    forbidden = {"draft_report", "draft_markdown", "research_notes", "full_prompt"} & set(raw)
    if forbidden:
        raise ValueError(
            "site publication input must not contain draft or prompt content: "
            + ",".join(sorted(forbidden))
        )

    candidate_id = _required_text(raw, "candidate_id")
    bucket = _required_text(raw, "bucket")
    status = _required_text(raw, "status")
    if status not in STATUSES:
        raise ValueError(f"candidate {candidate_id} has unsupported status: {status}")
    stage = _required_text(raw, "stage")
    if stage not in STAGES:
        raise ValueError(f"candidate {candidate_id} has unsupported stage: {stage}")

    observed_at = _aware_datetime(raw.get("observed_at"), "candidate observed_at")
    if observed_at > run_as_of:
        raise ValueError(f"candidate {candidate_id} is observed after the weekly run")
    first_detected_as_of = _required_text(raw, "first_detected_as_of")
    datetime.fromisoformat(first_detected_as_of)

    source_classes = _validate_source_classes(
        raw.get("source_classes"), f"candidate {candidate_id} source_classes"
    )
    evidence_count = _nonnegative_int(raw.get("evidence_count"), "evidence_count")
    if evidence_count < len(source_classes):
        raise ValueError(f"candidate {candidate_id} has fewer evidence rows than source classes")

    reason_code = raw.get("reason_code")
    reason_summary_ko = raw.get("reason_summary_ko")
    if status == "rejected":
        if not isinstance(reason_code, str) or not reason_code.strip():
            raise ValueError(f"rejected candidate {candidate_id} requires reason_code")
        if not isinstance(reason_summary_ko, str) or not 10 <= len(reason_summary_ko.strip()) <= 180:
            raise ValueError(
                f"rejected candidate {candidate_id} requires a 10-180 character Korean summary"
            )
    elif reason_code is not None or reason_summary_ko is not None:
        raise ValueError(f"non-rejected candidate {candidate_id} cannot carry a rejection reason")

    report_id = raw.get("report_id")
    if status == "final_report_published":
        if stage != "final_report":
            raise ValueError(f"published candidate {candidate_id} must be at final_report")
        if not isinstance(report_id, str) or not report_id.strip():
            raise ValueError(f"published candidate {candidate_id} requires report_id")
    elif report_id is not None:
        raise ValueError(f"candidate {candidate_id} cannot reference a report before publication")

    return {
        "candidate_id": candidate_id,
        "bucket": bucket,
        "status": status,
        "stage": stage,
        "stage_order": STAGES.index(stage),
        "observed_at": observed_at.isoformat(),
        "first_detected_as_of": first_detected_as_of,
        "evidence_count": evidence_count,
        "source_classes": source_classes,
        "reason_code": None if reason_code is None else str(reason_code).strip(),
        "reason_summary_ko": (
            None if reason_summary_ko is None else str(reason_summary_ko).strip()
        ),
        "report_id": None if report_id is None else str(report_id).strip(),
    }


def _normalize_report(raw: object, *, run_as_of: datetime) -> tuple[dict[str, object], dict[str, object]]:
    if not isinstance(raw, dict):
        raise ValueError("final report must be an object")
    forbidden = {"draft", "draft_markdown", "prompt", "research_notes"} & set(raw)
    if forbidden:
        raise ValueError(
            "final report publication metadata must not contain draft or prompt content: "
            + ",".join(sorted(forbidden))
        )

    report_id = _required_text(raw, "report_id")
    candidate_id = _required_text(raw, "candidate_id")
    title_ko = _required_text(raw, "title_ko", minimum=5)
    report_object_key = _required_text(raw, "report_object_key")
    report_sha256 = _required_text(raw, "report_sha256", minimum=64)
    if len(report_sha256) != 64 or any(c not in "0123456789abcdef" for c in report_sha256):
        raise ValueError(f"final report {report_id} has invalid report_sha256")
    published_at = _aware_datetime(raw.get("published_at"), "report published_at")
    if published_at > run_as_of:
        raise ValueError(f"final report {report_id} is published after the weekly run")

    source_classes = _validate_source_classes(
        raw.get("source_classes"), f"final report {report_id} source_classes"
    )
    independent_source_count = _nonnegative_int(
        raw.get("independent_source_count"), "independent_source_count"
    )
    if len(source_classes) < 4:
        raise ValueError(f"final report {report_id} requires at least four source classes")
    if len(set(source_classes) & INDEPENDENT_SOURCE_CLASSES) < 2:
        raise ValueError(f"final report {report_id} requires independent source diversity")
    if independent_source_count < 2:
        raise ValueError(f"final report {report_id} requires at least two independent sources")

    usage = raw.get("token_usage")
    if not isinstance(usage, dict):
        raise ValueError(f"final report {report_id} requires token_usage")
    input_tokens = _nonnegative_int(usage.get("input_tokens"), "input_tokens")
    output_tokens = _nonnegative_int(usage.get("output_tokens"), "output_tokens")
    cached_input_tokens = _nonnegative_int(
        usage.get("cached_input_tokens", 0), "cached_input_tokens"
    )
    if output_tokens == 0:
        raise ValueError(f"final report {report_id} requires non-zero output_tokens")
    if cached_input_tokens > input_tokens:
        raise ValueError(f"final report {report_id} cached tokens exceed input tokens")

    quality = raw.get("quality_feedback")
    if not isinstance(quality, dict):
        raise ValueError(f"final report {report_id} requires quality_feedback")
    useful_claim_count = _nonnegative_int(
        quality.get("useful_claim_count"), "useful_claim_count"
    )
    unsupported_claim_count = _nonnegative_int(
        quality.get("unsupported_claim_count"), "unsupported_claim_count"
    )
    unique_source_count = _nonnegative_int(
        quality.get("unique_source_count"), "unique_source_count"
    )
    duplicate_evidence_ratio = _number(
        quality.get("duplicate_evidence_ratio"), "duplicate_evidence_ratio"
    )
    if duplicate_evidence_ratio > 1:
        raise ValueError("duplicate_evidence_ratio must not exceed 1")
    if useful_claim_count == 0:
        raise ValueError(f"final report {report_id} requires useful claims")
    if unsupported_claim_count:
        raise ValueError(f"final report {report_id} cannot publish unsupported claims")
    if unique_source_count < independent_source_count:
        raise ValueError(f"final report {report_id} source counts are inconsistent")

    cache_share = 0.0 if input_tokens == 0 else cached_input_tokens / input_tokens
    output_tokens_per_useful_claim = output_tokens / useful_claim_count
    input_tokens_per_unique_source = (
        0.0 if unique_source_count == 0 else input_tokens / unique_source_count
    )
    recommendations: list[str] = []
    if input_tokens_per_unique_source > 4000:
        recommendations.append("다음 버전에서는 조사 묶음의 원문 길이와 반복 구간을 줄인다.")
    if output_tokens_per_useful_claim > 500:
        recommendations.append("최종 서술에서 반복 설명을 줄이고 핵심 주장 밀도를 높인다.")
    if duplicate_evidence_ratio > 0.15:
        recommendations.append("동일 근거의 반복 인용을 코드 단계에서 더 강하게 합친다.")
    if input_tokens >= 10000 and cache_share < 0.2:
        recommendations.append("변하지 않는 방법론·산업 정의 입력의 재사용률을 높인다.")
    if not recommendations:
        recommendations.append("현재 품질을 유지하며 다음 보고서와 비용을 비교한다.")

    report = {
        "report_id": report_id,
        "candidate_id": candidate_id,
        "title_ko": title_ko,
        "report_object_key": report_object_key,
        "report_sha256": report_sha256,
        "published_at": published_at.isoformat(),
        "source_classes": source_classes,
        "independent_source_count": independent_source_count,
        "token_usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_input_tokens": cached_input_tokens,
        },
    }
    feedback = {
        "schema_version": TOKEN_FEEDBACK_SCHEMA,
        "report_id": report_id,
        "candidate_id": candidate_id,
        "quality": {
            "useful_claim_count": useful_claim_count,
            "unsupported_claim_count": unsupported_claim_count,
            "unique_source_count": unique_source_count,
            "duplicate_evidence_ratio": round(duplicate_evidence_ratio, 6),
        },
        "efficiency": {
            "cache_share": round(cache_share, 6),
            "output_tokens_per_useful_claim": round(output_tokens_per_useful_claim, 2),
            "input_tokens_per_unique_source": round(input_tokens_per_unique_source, 2),
        },
        "recommendations_ko": recommendations,
    }
    return report, feedback


def build_weekly_site_export(payload: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    if payload.get("schema_version") != WEEKLY_RESEARCH_INPUT_SCHEMA:
        raise ValueError("unsupported weekly research input schema")
    if payload.get("cadence") != "weekly":
        raise ValueError("weekly research publication requires cadence=weekly")
    if payload.get("language") != "ko":
        raise ValueError("weekly research publication requires Korean-first output")

    run_id = _required_text(payload, "run_id")
    run_as_of = _aware_datetime(payload.get("as_of"), "weekly run as_of")

    raw_candidates = payload.get("candidates")
    raw_reports = payload.get("final_reports")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ValueError("weekly research input requires candidates")
    if not isinstance(raw_reports, list):
        raise ValueError("weekly research input final_reports must be a list")

    candidates = [_normalize_candidate(raw, run_as_of=run_as_of) for raw in raw_candidates]
    candidate_ids = [str(item["candidate_id"]) for item in candidates]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("weekly candidate IDs must be unique")

    reports: list[dict[str, object]] = []
    feedback_rows: list[dict[str, object]] = []
    for raw in raw_reports:
        report, feedback = _normalize_report(raw, run_as_of=run_as_of)
        reports.append(report)
        feedback_rows.append(feedback)
    report_ids = [str(item["report_id"]) for item in reports]
    if len(set(report_ids)) != len(report_ids):
        raise ValueError("weekly final report IDs must be unique")

    candidate_by_id = {str(item["candidate_id"]): item for item in candidates}
    report_by_id = {str(item["report_id"]): item for item in reports}
    for report in reports:
        candidate = candidate_by_id.get(str(report["candidate_id"]))
        if candidate is None:
            raise ValueError(f"final report {report['report_id']} has no weekly candidate")
        if candidate["status"] != "final_report_published":
            raise ValueError(f"final report {report['report_id']} candidate is not published")
        if candidate["report_id"] != report["report_id"]:
            raise ValueError(f"final report {report['report_id']} candidate linkage differs")
    for candidate in candidates:
        report_id = candidate["report_id"]
        if report_id is not None and str(report_id) not in report_by_id:
            raise ValueError(f"published candidate {candidate['candidate_id']} has no final report")

    compact_statuses = [
        {
            "candidate_id": item["candidate_id"],
            "bucket": item["bucket"],
            "status": item["status"],
            "stage": item["stage"],
            "stage_order": item["stage_order"],
            "observed_at": item["observed_at"],
            "first_detected_as_of": item["first_detected_as_of"],
            "reason_code": item["reason_code"],
            "reason_summary_ko": item["reason_summary_ko"],
            "report_id": item["report_id"],
        }
        for item in candidates
    ]
    site_export: dict[str, object] = {
        "schema_version": WEEKLY_SITE_EXPORT_SCHEMA,
        "run_id": run_id,
        "as_of": run_as_of.isoformat(),
        "cadence": "weekly",
        "language": "ko",
        "publication_policy": {
            "final_reports_only": True,
            "draft_content_stored": False,
            "compact_rejection_statuses": True,
            "gpt_v1_quality_priority": True,
        },
        "research_policy": V1_RESEARCH_POLICY,
        "summary": {
            "candidate_count": len(candidates),
            "active_research_count": sum(
                item["status"] == "active_research" for item in candidates
            ),
            "rejected_count": sum(item["status"] == "rejected" for item in candidates),
            "final_report_count": len(reports),
        },
        "candidate_statuses": compact_statuses,
        "final_reports": reports,
    }
    site_export["export_sha256"] = _canonical_sha256(site_export)

    feedback_export: dict[str, object] = {
        "schema_version": TOKEN_FEEDBACK_SCHEMA,
        "run_id": run_id,
        "as_of": run_as_of.isoformat(),
        "report_count": len(feedback_rows),
        "reports": feedback_rows,
    }
    feedback_export["feedback_sha256"] = _canonical_sha256(feedback_export)
    return site_export, feedback_export


def write_weekly_site_artifacts(
    output_dir: Path,
    site_export: dict[str, object],
    feedback_export: dict[str, object],
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    site_path = output_dir / "weekly_research_status.json"
    feedback_path = output_dir / "token_efficiency_feedback.json"
    site_path.write_text(
        json.dumps(site_export, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    feedback_path.write_text(
        json.dumps(feedback_export, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return site_path, feedback_path
