from __future__ import annotations

from dataclasses import dataclass

from .transcript_pipeline import infer_turn_sections
from .transcripts import EarningsCallTranscript


@dataclass(frozen=True)
class TranscriptQuality:
    ticker: str
    quarter: str
    turn_count: int
    speaker_labeled_turns: int
    title_labeled_turns: int
    prepared_turns: int
    qa_turns: int

    @property
    def speaker_label_rate(self) -> float:
        return 0.0 if self.turn_count == 0 else self.speaker_labeled_turns / self.turn_count

    @property
    def title_label_rate(self) -> float:
        return 0.0 if self.turn_count == 0 else self.title_labeled_turns / self.turn_count

    @property
    def qa_detected(self) -> bool:
        return self.qa_turns > 0


@dataclass(frozen=True)
class TranscriptQualitySummary:
    transcript_count: int
    total_turns: int
    average_turns: float
    speaker_label_rate: float
    title_label_rate: float
    transcripts_with_qa: int
    qa_detection_rate: float
    records: tuple[TranscriptQuality, ...]


def evaluate_transcript_quality(transcripts: tuple[EarningsCallTranscript, ...]) -> TranscriptQualitySummary:
    records: list[TranscriptQuality] = []
    for transcript in transcripts:
        sections = infer_turn_sections(transcript)
        records.append(
            TranscriptQuality(
                ticker=transcript.ticker,
                quarter=transcript.fiscal_quarter,
                turn_count=len(transcript.turns),
                speaker_labeled_turns=sum(bool(turn.speaker) for turn in transcript.turns),
                title_labeled_turns=sum(bool(turn.title) for turn in transcript.turns),
                prepared_turns=sum(section == "prepared" for section in sections),
                qa_turns=sum(section == "qa" for section in sections),
            )
        )

    total_turns = sum(record.turn_count for record in records)
    speaker_labeled = sum(record.speaker_labeled_turns for record in records)
    title_labeled = sum(record.title_labeled_turns for record in records)
    with_qa = sum(record.qa_detected for record in records)
    count = len(records)
    return TranscriptQualitySummary(
        transcript_count=count,
        total_turns=total_turns,
        average_turns=(total_turns / count if count else 0.0),
        speaker_label_rate=(speaker_labeled / total_turns if total_turns else 0.0),
        title_label_rate=(title_labeled / total_turns if total_turns else 0.0),
        transcripts_with_qa=with_qa,
        qa_detection_rate=(with_qa / count if count else 0.0),
        records=tuple(records),
    )
