from pathlib import Path

from industry_bottleneck_scanner.transcript_store import FileTranscriptStore
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn
from industry_bottleneck_scanner.v2_source_provenance import (
    SourceResolutionRecord,
    compute_v2_source_resolution_fingerprint,
    missing_resolved_transcripts,
    provider_mix_summary,
)


def _save(root: Path, provider: str, ticker: str, quarter: str, text: str) -> None:
    FileTranscriptStore(root).save(
        EarningsCallTranscript(
            provider=provider,
            ticker=ticker,
            fiscal_quarter=quarter,
            turns=(TranscriptTurn(speaker="CEO", title="CEO", text=text),),
        )
    )


def test_provider_mix_summary_counts_issuers_and_quarters() -> None:
    records = (
        SourceResolutionRecord("aaa", "alpha_vantage", ("2026Q1", "2026Q2")),
        SourceResolutionRecord("bbb", "quartr_edited", ("2026Q1", "2026Q2")),
        SourceResolutionRecord("ccc", "alpha_vantage", ("2026Q1", "2026Q2")),
    )

    assert provider_mix_summary(records) == {
        "alpha_vantage": {"issuers": 2, "ticker_quarters": 4},
        "quartr_edited": {"issuers": 1, "ticker_quarters": 2},
    }


def test_missing_resolved_transcripts_preserves_provider_identity(tmp_path: Path) -> None:
    _save(tmp_path, "alpha_vantage", "AAA", "2026Q1", "baseline")
    records = (SourceResolutionRecord("AAA", "alpha_vantage", ("2026Q1", "2026Q2")),)

    assert missing_resolved_transcripts(records, transcript_root=tmp_path) == (
        "alpha_vantage:AAA:2026Q2",
    )


def test_fingerprint_changes_when_provider_selection_or_transcript_changes(tmp_path: Path) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text('{"hierarchy":["alpha_vantage","quartr_edited"]}\n', encoding="utf-8")
    transcript_root = tmp_path / "transcripts"
    _save(transcript_root, "alpha_vantage", "AAA", "2026Q1", "primary baseline")
    _save(transcript_root, "alpha_vantage", "AAA", "2026Q2", "primary current")
    _save(transcript_root, "quartr_edited", "AAA", "2026Q1", "fallback baseline")
    _save(transcript_root, "quartr_edited", "AAA", "2026Q2", "fallback current")

    primary = (SourceResolutionRecord("AAA", "alpha_vantage", ("2026Q1", "2026Q2")),)
    fallback = (SourceResolutionRecord("AAA", "quartr_edited", ("2026Q1", "2026Q2")),)

    primary_hash = compute_v2_source_resolution_fingerprint(
        primary,
        source_policy_path=policy,
        transcript_root=transcript_root,
    )
    fallback_hash = compute_v2_source_resolution_fingerprint(
        fallback,
        source_policy_path=policy,
        transcript_root=transcript_root,
    )
    assert primary_hash != fallback_hash

    _save(transcript_root, "alpha_vantage", "AAA", "2026Q2", "changed primary current")
    changed_hash = compute_v2_source_resolution_fingerprint(
        primary,
        source_policy_path=policy,
        transcript_root=transcript_root,
    )
    assert changed_hash != primary_hash
