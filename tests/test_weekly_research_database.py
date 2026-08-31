from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


MIGRATION = Path("web_contract/migrations/0001_weekly_research.sql")


def database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.executescript(MIGRATION.read_text(encoding="utf-8"))
    return connection


def insert_run(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO weekly_runs(run_id, as_of, cadence, language, export_sha256) "
        "VALUES (?, ?, ?, ?, ?)",
        ("weekly-1", "2026-08-31T12:00:00+00:00", "weekly", "ko", "a" * 64),
    )


def test_schema_has_status_and_final_tables_but_no_draft_storage() -> None:
    connection = database()
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    columns = {
        row[1]
        for table in tables
        for row in connection.execute(f"PRAGMA table_info({table})")
    }

    assert {
        "weekly_runs",
        "industry_statuses",
        "final_reports",
        "report_efficiency_feedback",
    } <= tables
    assert not any("draft" in table for table in tables)
    assert not any("draft" in column or "prompt" in column for column in columns)


def test_rejection_row_requires_stage_and_compact_reason() -> None:
    connection = database()
    insert_run(connection)

    connection.execute(
        "INSERT INTO industry_statuses "
        "(run_id, candidate_id, bucket, status, stage, stage_order, observed_at, "
        "first_detected_as_of, reason_code, reason_summary_ko, report_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "weekly-1",
            "insurance",
            "손해·건강보험",
            "rejected",
            "operating_evidence",
            2,
            "2026-08-31T10:00:00+00:00",
            "2026-08-21",
            "sparse_evidence",
            "직접 운영 근거가 한 개 기업에만 있어 산업 전반으로 일반화할 수 없습니다.",
            None,
        ),
    )

    row = connection.execute(
        "SELECT stage, reason_summary_ko FROM industry_statuses WHERE candidate_id = ?",
        ("insurance",),
    ).fetchone()
    assert row is not None
    assert row[0] == "operating_evidence"
    assert "한 개 기업" in row[1]

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO industry_statuses "
            "(run_id, candidate_id, bucket, status, stage, stage_order, observed_at, "
            "first_detected_as_of) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "weekly-1",
                "bad-reject",
                "사유 없는 산업",
                "rejected",
                "market_screen",
                0,
                "2026-08-31T10:00:00+00:00",
                "2026-08-31",
            ),
        )


def test_only_published_status_can_receive_final_report() -> None:
    connection = database()
    insert_run(connection)
    connection.execute(
        "INSERT INTO industry_statuses "
        "(run_id, candidate_id, bucket, status, stage, stage_order, observed_at, "
        "first_detected_as_of, report_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "weekly-1",
            "lpt",
            "대형 전력변압기",
            "final_report_published",
            "final_report",
            8,
            "2026-08-31T10:00:00+00:00",
            "2025-08-29",
            "report-1",
        ),
    )
    connection.execute(
        "INSERT INTO final_reports "
        "(report_id, run_id, candidate_id, title_ko, report_object_key, report_sha256, "
        "published_at, source_classes_json, independent_source_count, input_tokens, "
        "output_tokens, cached_input_tokens) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "report-1",
            "weekly-1",
            "lpt",
            "대형 전력변압기 최종 분석",
            "reports/report-1.json",
            "b" * 64,
            "2026-08-31T11:00:00+00:00",
            '["issuer_primary","government_regulator","industry_technical","physical_market_data"]',
            4,
            20000,
            6000,
            5000,
        ),
    )

    assert connection.execute("SELECT count(*) FROM final_reports").fetchone()[0] == 1
