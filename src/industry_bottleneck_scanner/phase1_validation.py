from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

ValidationRole = Literal["positive", "control", "blind"]
ValidationAggregationLevel = Literal["sector", "industry", "subindustry"]


@dataclass(frozen=True)
class ValidationCase:
    case_id: str
    role: ValidationRole
    result_path: str
    aggregation_level: ValidationAggregationLevel
    expected_bucket: str | None = None
    expected_metrics: tuple[str, ...] = ()
    label_sources: tuple[str, ...] = ()
    notes: str | None = None


@dataclass(frozen=True)
class CaseEvaluation:
    case_id: str
    role: ValidationRole
    result_path: str
    aggregation_level: ValidationAggregationLevel
    aggregation_level_matches: bool
    label_sources: tuple[str, ...]
    strongest_bucket: str | None
    strongest_stage: str | None
    strongest_score: float | None
    expected_bucket_found: bool | None
    expected_bucket_stage: str | None
    expected_metric_hits: tuple[str, ...]
    expected_metric_misses: tuple[str, ...]
    positive_recovered: bool | None
    control_false_positive: bool | None


@dataclass(frozen=True)
class ValidationSummary:
    total_cases: int
    positive_cases: int
    control_cases: int
    blind_cases: int
    aggregation_mismatches: int
    positive_recovered: int
    positive_recall: float | None
    controls_false_positive: int
    control_false_positive_rate: float | None
    expected_metric_hits: int
    expected_metric_total: int
    expected_metric_recall: float | None


@dataclass(frozen=True)
class ValidationReport:
    summary: ValidationSummary
    cases: tuple[CaseEvaluation, ...]


def _parse_pipe_list(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(dict.fromkeys(item.strip() for item in value.split("|") if item.strip()))


def _validate_sources(sources: tuple[str, ...], *, row_number: int) -> tuple[str, ...]:
    for source in sources:
        parsed = urlparse(source)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"row {row_number}: label_sources must contain http(s) URLs")
    return sources


def load_validation_cases_csv(text: str) -> tuple[ValidationCase, ...]:
    reader = csv.DictReader(StringIO(text))
    required = {"case_id", "role", "result_path", "aggregation_level"}
    missing = required - set(reader.fieldnames or ())
    if missing:
        raise ValueError(f"validation manifest missing required columns: {sorted(missing)}")

    cases: list[ValidationCase] = []
    seen: set[str] = set()
    for row_number, row in enumerate(reader, start=2):
        case_id = (row.get("case_id") or "").strip()
        role = (row.get("role") or "").strip().lower()
        result_path = (row.get("result_path") or "").strip()
        aggregation_level = (row.get("aggregation_level") or "").strip().lower()
        expected_bucket = (row.get("expected_bucket") or "").strip() or None
        notes = (row.get("notes") or "").strip() or None
        if not case_id or not result_path:
            raise ValueError(f"row {row_number}: case_id and result_path are required")
        if case_id in seen:
            raise ValueError(f"row {row_number}: duplicate case_id {case_id!r}")
        if role not in {"positive", "control", "blind"}:
            raise ValueError(f"row {row_number}: role must be positive, control, or blind")
        if aggregation_level not in {"sector", "industry", "subindustry"}:
            raise ValueError(f"row {row_number}: aggregation_level must be sector, industry, or subindustry")
        if role == "positive" and not expected_bucket:
            raise ValueError(f"row {row_number}: positive cases require expected_bucket")
        if role != "positive" and expected_bucket:
            raise ValueError(f"row {row_number}: expected_bucket is only valid for positive cases")

        expected_metrics = _parse_pipe_list(row.get("expected_metrics"))
        label_sources = _validate_sources(_parse_pipe_list(row.get("label_sources")), row_number=row_number)
        if role == "positive" and not label_sources:
            raise ValueError(f"row {row_number}: positive cases require at least one label source URL")

        seen.add(case_id)
        cases.append(
            ValidationCase(
                case_id=case_id,
                role=role,  # type: ignore[arg-type]
                result_path=result_path,
                aggregation_level=aggregation_level,  # type: ignore[arg-type]
                expected_bucket=expected_bucket,
                expected_metrics=expected_metrics,
                label_sources=label_sources,
                notes=notes,
            )
        )
    if not cases:
        raise ValueError("validation manifest must contain at least one case")
    return tuple(cases)


def _stage_rank(stage: str | None) -> int:
    return {"observing": 0, "watchlisted": 1, "triggered": 2, "confirmed": 3}.get(stage or "", -1)


def _snapshot_stage(item: dict[str, object]) -> str:
    score = item.get("discovery_score")
    if isinstance(score, dict) and isinstance(score.get("stage"), str):
        return str(score["stage"])
    if item.get("confirmed") is True:
        return "confirmed"
    if item.get("triggered") is True:
        return "triggered"
    if item.get("watchlisted") is True:
        return "watchlisted"
    return "observing"


def _snapshot_score(item: dict[str, object]) -> float:
    score = item.get("discovery_score")
    if isinstance(score, dict):
        value = score.get("score")
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


def _load_result(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: result JSON must be an object")
    acceleration = payload.get("acceleration")
    if not isinstance(acceleration, list):
        raise ValueError(f"{path}: result JSON must contain acceleration list")
    return payload


def evaluate_validation_case(case: ValidationCase, *, base_dir: Path = Path(".")) -> CaseEvaluation:
    result_path = Path(case.result_path)
    if not result_path.is_absolute():
        result_path = base_dir / result_path
    payload = _load_result(result_path)
    acceleration = [item for item in payload["acceleration"] if isinstance(item, dict)]  # type: ignore[index]
    result_level = payload.get("aggregation_level")
    aggregation_level_matches = result_level == case.aggregation_level

    strongest = max(
        acceleration,
        key=lambda item: (_stage_rank(_snapshot_stage(item)), _snapshot_score(item), str(item.get("bucket", ""))),
        default=None,
    )
    strongest_bucket = str(strongest.get("bucket")) if strongest and strongest.get("bucket") is not None else None
    strongest_stage = _snapshot_stage(strongest) if strongest else None
    strongest_score = _snapshot_score(strongest) if strongest else None

    expected = None
    if case.expected_bucket:
        expected = next((item for item in acceleration if item.get("bucket") == case.expected_bucket), None)
    expected_bucket_found = expected is not None if case.role == "positive" else None
    expected_bucket_stage = _snapshot_stage(expected) if expected else None

    active_metrics: set[str] = set()
    if expected:
        current = payload.get("current")
        if isinstance(current, dict):
            clusters = current.get("clusters")
            if isinstance(clusters, list):
                cluster = next(
                    (item for item in clusters if isinstance(item, dict) and item.get("bucket") == case.expected_bucket),
                    None,
                )
                if isinstance(cluster, dict):
                    metrics = cluster.get("active_metrics")
                    if isinstance(metrics, list):
                        active_metrics = {str(item) for item in metrics}
    metric_hits = tuple(metric for metric in case.expected_metrics if metric in active_metrics)
    metric_misses = tuple(metric for metric in case.expected_metrics if metric not in active_metrics)

    positive_recovered: bool | None = None
    if case.role == "positive":
        positive_recovered = bool(
            aggregation_level_matches
            and expected
            and _stage_rank(expected_bucket_stage) >= _stage_rank("watchlisted")
            and not metric_misses
        )

    control_false_positive: bool | None = None
    if case.role == "control":
        control_false_positive = bool(
            aggregation_level_matches
            and any(_stage_rank(_snapshot_stage(item)) >= _stage_rank("triggered") for item in acceleration)
        )

    return CaseEvaluation(
        case_id=case.case_id,
        role=case.role,
        result_path=str(result_path),
        aggregation_level=case.aggregation_level,
        aggregation_level_matches=aggregation_level_matches,
        label_sources=case.label_sources,
        strongest_bucket=strongest_bucket,
        strongest_stage=strongest_stage,
        strongest_score=strongest_score,
        expected_bucket_found=expected_bucket_found,
        expected_bucket_stage=expected_bucket_stage,
        expected_metric_hits=metric_hits,
        expected_metric_misses=metric_misses,
        positive_recovered=positive_recovered,
        control_false_positive=control_false_positive,
    )


def evaluate_validation_manifest(
    cases: tuple[ValidationCase, ...],
    *,
    base_dir: Path = Path("."),
) -> ValidationReport:
    evaluations = tuple(evaluate_validation_case(case, base_dir=base_dir) for case in cases)
    positives = [item for item in evaluations if item.role == "positive"]
    controls = [item for item in evaluations if item.role == "control"]
    blinds = [item for item in evaluations if item.role == "blind"]
    recovered = sum(item.positive_recovered is True for item in positives)
    false_positives = sum(item.control_false_positive is True for item in controls)
    metric_hits = sum(len(item.expected_metric_hits) for item in positives)
    metric_total = sum(len(item.expected_metric_hits) + len(item.expected_metric_misses) for item in positives)

    summary = ValidationSummary(
        total_cases=len(evaluations),
        positive_cases=len(positives),
        control_cases=len(controls),
        blind_cases=len(blinds),
        aggregation_mismatches=sum(not item.aggregation_level_matches for item in evaluations),
        positive_recovered=recovered,
        positive_recall=(recovered / len(positives)) if positives else None,
        controls_false_positive=false_positives,
        control_false_positive_rate=(false_positives / len(controls)) if controls else None,
        expected_metric_hits=metric_hits,
        expected_metric_total=metric_total,
        expected_metric_recall=(metric_hits / metric_total) if metric_total else None,
    )
    return ValidationReport(summary=summary, cases=evaluations)
