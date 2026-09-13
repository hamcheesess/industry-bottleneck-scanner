from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from .transcripts import EarningsCallTranscript

_MONTH_NAMES = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
)
_MONTH_FIRST = re.compile(
    rf"\b(?P<month>{_MONTH_NAMES})\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?(?:,)?\s+(?P<year>20\d{{2}})\b",
    re.IGNORECASE,
)
_DAY_FIRST = re.compile(
    rf"\b(?P<day>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<month>{_MONTH_NAMES})\s+(?P<year>20\d{{2}})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExplicitDateEvidence:
    value: date
    turn_index: int
    evidence_text: str


def _parse_match(match: re.Match[str]) -> date | None:
    text = f"{match.group('month')} {match.group('day')} {match.group('year')}"
    try:
        return datetime.strptime(text.title(), "%B %d %Y").date()
    except ValueError:
        return None


def find_explicit_transcript_dates(
    transcript: EarningsCallTranscript,
    *,
    max_turns: int = 20,
) -> tuple[ExplicitDateEvidence, ...]:
    """Find unambiguous written calendar dates in early transcript turns.

    This helper is deliberately conservative. It does not derive a date from the fiscal
    quarter, does not interpret numeric-only dates, and does not invent a call time or
    timezone. The output is only a research hint for building audited metadata.
    """

    if max_turns < 1:
        raise ValueError("max_turns must be at least 1")

    found: list[ExplicitDateEvidence] = []
    seen: set[tuple[date, int]] = set()
    for index, turn in enumerate(transcript.turns[:max_turns]):
        for pattern in (_MONTH_FIRST, _DAY_FIRST):
            for match in pattern.finditer(turn.text):
                value = _parse_match(match)
                if value is None:
                    continue
                key = (value, index)
                if key in seen:
                    continue
                seen.add(key)
                snippet = turn.text.strip()
                if len(snippet) > 320:
                    start = max(0, match.start() - 120)
                    end = min(len(snippet), match.end() + 120)
                    snippet = snippet[start:end].strip()
                found.append(
                    ExplicitDateEvidence(
                        value=value,
                        turn_index=index,
                        evidence_text=snippet,
                    )
                )
    return tuple(found)


def choose_explicit_call_date(
    transcript: EarningsCallTranscript,
    *,
    max_turns: int = 20,
) -> ExplicitDateEvidence | None:
    """Return one explicit date only when the early transcript is unambiguous.

    Multiple mentions of the same calendar date are acceptable. If distinct dates appear,
    no date is selected. This prevents dates mentioned in legal notices, historical
    comparisons, or prepared remarks from silently becoming publication metadata.
    """

    candidates = find_explicit_transcript_dates(transcript, max_turns=max_turns)
    values = {item.value for item in candidates}
    if len(values) != 1:
        return None
    selected_value = next(iter(values))
    return next(item for item in candidates if item.value == selected_value)


def count_unique_dates(items: Iterable[ExplicitDateEvidence]) -> int:
    return len({item.value for item in items})
