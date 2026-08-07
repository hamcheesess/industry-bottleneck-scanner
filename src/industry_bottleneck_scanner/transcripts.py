from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TranscriptTurn:
    speaker: str | None
    title: str | None
    text: str
    sentiment: float | None = None


@dataclass(frozen=True)
class EarningsCallTranscript:
    provider: str
    ticker: str
    fiscal_quarter: str
    turns: tuple[TranscriptTurn, ...]
    source_url: str | None = None

    @property
    def full_text(self) -> str:
        return "\n".join(turn.text for turn in self.turns if turn.text.strip())

    @property
    def is_empty(self) -> bool:
        return not any(turn.text.strip() for turn in self.turns)


class TranscriptSource(Protocol):
    provider_name: str

    def fetch(self, *, ticker: str, quarter: str) -> EarningsCallTranscript | None:
        """Return one earnings-call transcript or None when the provider has no record.

        Implementations must not invoke any LLM. They only retrieve and normalize source data.
        """
        ...
