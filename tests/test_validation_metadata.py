from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn
from industry_bottleneck_scanner.validation_metadata import (
    choose_explicit_call_date,
    find_explicit_transcript_dates,
)


def _transcript(*texts: str) -> EarningsCallTranscript:
    return EarningsCallTranscript(
        provider="alpha_vantage",
        ticker="AAA",
        fiscal_quarter="2026Q2",
        turns=tuple(TranscriptTurn(speaker=None, title=None, text=text) for text in texts),
        source_url=None,
    )


def test_choose_explicit_call_date_accepts_one_written_date() -> None:
    transcript = _transcript(
        "Welcome to the call on August 13, 2026.",
        "We appreciate everyone joining today.",
    )

    evidence = choose_explicit_call_date(transcript)

    assert evidence is not None
    assert evidence.value.isoformat() == "2026-08-13"
    assert evidence.turn_index == 0


def test_choose_explicit_call_date_rejects_multiple_distinct_dates() -> None:
    transcript = _transcript(
        "Welcome to the call on August 13, 2026.",
        "Our prior update was issued on May 5, 2026.",
    )

    assert choose_explicit_call_date(transcript) is None
    assert len(find_explicit_transcript_dates(transcript)) == 2


def test_date_extractor_does_not_infer_from_fiscal_quarter() -> None:
    transcript = _transcript("Welcome to our second-quarter earnings call.")

    assert choose_explicit_call_date(transcript) is None
