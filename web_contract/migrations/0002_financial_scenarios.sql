PRAGMA foreign_keys = ON;

ALTER TABLE industry_statuses ADD COLUMN financial_scenario_id TEXT;

CREATE UNIQUE INDEX industry_statuses_financial_scenario_idx
    ON industry_statuses(financial_scenario_id)
    WHERE financial_scenario_id IS NOT NULL;

CREATE TABLE financial_scenario_summaries (
    scenario_run_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    as_of TEXT NOT NULL,
    readiness_status TEXT NOT NULL CHECK (
        readiness_status IN ('screen_grade', 'senior_review_ready')
    ),
    decision_status TEXT NOT NULL CHECK (
        decision_status IN (
            'advance_to_deeper_work',
            'wait_for_proof',
            'valuation_gated',
            'reject_no_expectation_gap',
            'reject_unfavorable_skew'
        )
    ),
    gate_reasons_json TEXT NOT NULL,
    base_12m_return REAL NOT NULL,
    downside_12m_return REAL NOT NULL,
    upside_12m_return REAL NOT NULL,
    reward_to_downside REAL,
    base_12m_operating_income_gap REAL NOT NULL,
    base_12m_fcf_gap REAL NOT NULL,
    scenario_object_key TEXT NOT NULL UNIQUE,
    scenario_sha256 TEXT NOT NULL CHECK (length(scenario_sha256) = 64),
    investor_summary_ko_json TEXT NOT NULL,
    UNIQUE (run_id, candidate_id),
    FOREIGN KEY (run_id, candidate_id)
        REFERENCES industry_statuses(run_id, candidate_id),
    CHECK (
        (decision_status = 'advance_to_deeper_work' AND gate_reasons_json = '[]')
        OR
        (decision_status <> 'advance_to_deeper_work' AND gate_reasons_json <> '[]')
    )
);

CREATE TRIGGER financial_scenario_requires_candidate_link
BEFORE INSERT ON financial_scenario_summaries
FOR EACH ROW
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
        FROM industry_statuses status
        WHERE status.run_id = NEW.run_id
          AND status.candidate_id = NEW.candidate_id
          AND status.financial_scenario_id = NEW.scenario_run_id
    ) THEN RAISE(ABORT, 'financial scenario requires matching candidate linkage') END;
END;

CREATE INDEX financial_scenario_decision_idx
    ON financial_scenario_summaries(run_id, decision_status, base_12m_return DESC);

CREATE TRIGGER final_report_requires_advanced_financial_scenario
BEFORE INSERT ON final_reports
FOR EACH ROW
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
        FROM financial_scenario_summaries scenario
        WHERE scenario.run_id = NEW.run_id
          AND scenario.candidate_id = NEW.candidate_id
          AND scenario.decision_status = 'advance_to_deeper_work'
    ) THEN RAISE(ABORT, 'final report requires an advanced financial scenario') END;
END;
