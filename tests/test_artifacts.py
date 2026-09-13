import json
from datetime import datetime, timezone

from industry_bottleneck_scanner.artifacts import write_atomic_signals_jsonl
from industry_bottleneck_scanner.models import AtomicSignal, Classification


def test_atomic_signal_jsonl_preserves_provenance_and_datetime(tmp_path) -> None:
    signal = AtomicSignal(
        signal_id="sig-1",
        scanner="scarcity",
        metric="capacity_constraint",
        direction="strengthening",
        magnitude="unknown",
        company_id="issuer-powl",
        ticker="POWL",
        classification=Classification(industry="Electrical Equipment"),
        subject=None,
        document_id="doc-1",
        document_type="earnings_call_turn",
        published_at=datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc),
        source_url=None,
        evidence_text="Capacity remains constrained.",
        negated=False,
        resolved=False,
        extraction_method="keyword",
        confidence=0.9,
        matched_phrase="capacity remains constrained",
        source_section="qa",
        speaker="CEO",
        speaker_title="Chief Executive Officer",
    )
    path = tmp_path / "signals.jsonl"

    assert write_atomic_signals_jsonl(path, (signal,)) == 1
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["signal_id"] == "sig-1"
    assert payload["published_at"] == "2026-05-06T20:00:00+00:00"
    assert payload["source_section"] == "qa"
    assert payload["speaker"] == "CEO"
    assert payload["subject"] is None
