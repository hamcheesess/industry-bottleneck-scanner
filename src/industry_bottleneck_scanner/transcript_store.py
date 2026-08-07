from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .transcripts import EarningsCallTranscript, TranscriptTurn
from .universe import normalize_ticker


class FileTranscriptStore:
    """Local JSON cache for normalized transcripts.

    Raw provider responses are intentionally not stored. The cache contains only the
    normalized transcript contract used by the scanner. Runtime cache paths should live
    under ``var/`` so they remain outside Git history.
    """

    def __init__(self, root: Path = Path("var/transcripts")) -> None:
        self.root = root

    def path_for(self, *, provider: str, ticker: str, quarter: str) -> Path:
        return self.root / provider / normalize_ticker(ticker) / f"{quarter.upper()}.json"

    def load(self, *, provider: str, ticker: str, quarter: str) -> EarningsCallTranscript | None:
        path = self.path_for(provider=provider, ticker=ticker, quarter=quarter)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        turns = tuple(TranscriptTurn(**item) for item in payload["turns"])
        return EarningsCallTranscript(
            provider=payload["provider"],
            ticker=payload["ticker"],
            fiscal_quarter=payload["fiscal_quarter"],
            turns=turns,
            source_url=payload.get("source_url"),
        )

    def save(self, transcript: EarningsCallTranscript) -> Path:
        path = self.path_for(
            provider=transcript.provider,
            ticker=transcript.ticker,
            quarter=transcript.fiscal_quarter,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "provider": transcript.provider,
            "ticker": transcript.ticker,
            "fiscal_quarter": transcript.fiscal_quarter,
            "source_url": transcript.source_url,
            "turns": [asdict(turn) for turn in transcript.turns],
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path
