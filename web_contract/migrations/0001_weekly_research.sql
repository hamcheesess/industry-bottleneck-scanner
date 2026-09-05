PRAGMA foreign_keys = ON;

CREATE TABLE weekly_runs (
    run_id TEXT PRIMARY KEY,
    as_of TEXT NOT NULL,
    cadence TEXT NOT NULL CHECK (cadence = 'weekly'),
    language TEXT NOT NULL CHECK (language = 'ko'),
    export_sha256 TEXT NOT NULL CHECK (length(export_sha256) = 64),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE industry_statuses (
    run_id TEXT NOT NULL REFERENCES weekly_runs(run_id),
    candidate_id TEXT NOT NULL,
    bucket TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('active_research', 'rejected', 'final_report_published')
    ),
    stage TEXT NOT NULL CHECK (
        stage IN (
            'market_screen',
            'persistence',
            'operating_evidence',
            'causal_validation',
            'bottleneck_quantification',
            'issuer_exposure',
            'financial_translation',
            'expectations_gap',
            'final_report'
        )
    ),
    stage_order INTEGER NOT NULL CHECK (stage_order BETWEEN 0 AND 8),
    observed_at TEXT NOT NULL,
    first_detected_as_of TEXT NOT NULL,
    reason_code TEXT,
    reason_summary_ko TEXT CHECK (
        reason_summary_ko IS NULL OR length(reason_summary_ko) BETWEEN 10 AND 180
    ),
    report_id TEXT,
    PRIMARY KEY (run_id, candidate_id),
    CHECK (
        (status = 'rejected' AND reason_code IS NOT NULL AND reason_summary_ko IS NOT NULL)
        OR
        (status <> 'rejected' AND reason_code IS NULL AND reason_summary_ko IS NULL)
    ),
    CHECK (
        (status = 'final_report_published' AND stage = 'final_report' AND report_id IS NOT NULL)
        OR
        (status <> 'final_report_published' AND report_id IS NULL)
    )
);

CREATE INDEX industry_statuses_latest_idx
    ON industry_statuses(candidate_id, observed_at DESC);
CREATE INDEX industry_statuses_stage_idx
    ON industry_statuses(run_id, stage_order, status);

CREATE TABLE final_reports (
    report_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES weekly_runs(run_id),
    candidate_id TEXT NOT NULL,
    title_ko TEXT NOT NULL,
    report_object_key TEXT NOT NULL UNIQUE,
    report_sha256 TEXT NOT NULL CHECK (length(report_sha256) = 64),
    published_at TEXT NOT NULL,
    source_classes_json TEXT NOT NULL,
    independent_source_count INTEGER NOT NULL CHECK (independent_source_count >= 2),
    input_tokens INTEGER NOT NULL CHECK (input_tokens >= 0),
    output_tokens INTEGER NOT NULL CHECK (output_tokens > 0),
    cached_input_tokens INTEGER NOT NULL CHECK (
        cached_input_tokens >= 0 AND cached_input_tokens <= input_tokens
    ),
    UNIQUE (run_id, candidate_id),
    FOREIGN KEY (run_id, candidate_id)
        REFERENCES industry_statuses(run_id, candidate_id)
);

CREATE TABLE report_efficiency_feedback (
    report_id TEXT PRIMARY KEY REFERENCES final_reports(report_id),
    useful_claim_count INTEGER NOT NULL CHECK (useful_claim_count > 0),
    unsupported_claim_count INTEGER NOT NULL CHECK (unsupported_claim_count = 0),
    unique_source_count INTEGER NOT NULL CHECK (unique_source_count >= 2),
    duplicate_evidence_ratio REAL NOT NULL CHECK (
        duplicate_evidence_ratio BETWEEN 0 AND 1
    ),
    cache_share REAL NOT NULL CHECK (cache_share BETWEEN 0 AND 1),
    output_tokens_per_useful_claim REAL NOT NULL CHECK (
        output_tokens_per_useful_claim > 0
    ),
    input_tokens_per_unique_source REAL NOT NULL CHECK (
        input_tokens_per_unique_source >= 0
    ),
    recommendations_ko_json TEXT NOT NULL
);

-- Deliberately absent: draft reports, prompts, chain-of-thought, and raw research notes.
