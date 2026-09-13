from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .alpha_vantage import TranscriptProviderError
from .transcripts import EarningsCallTranscript, TranscriptTurn
from .universe import normalize_ticker

JsonObject = Mapping[str, Any]
MetadataTransport = Callable[[str, Mapping[str, str]], JsonObject]
FileTransport = Callable[[str], JsonObject]


def _default_metadata_transport(url: str, headers: Mapping[str, str]) -> JsonObject:
    request = Request(url, headers=dict(headers))
    with urlopen(request, timeout=30) as response:  # noqa: S310 - provider URL is fixed by adapter
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise TranscriptProviderError("Quartr returned a non-object JSON payload")
    return payload


def _default_file_transport(url: str) -> JsonObject:
    request = Request(url, headers={"User-Agent": "industry-bottleneck-scanner/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - URL comes from authenticated Quartr metadata
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise TranscriptProviderError("Quartr transcript file returned a non-object JSON payload")
    return payload


def _validate_quarter(value: str) -> tuple[str, int, str]:
    normalized = value.strip().upper()
    if len(normalized) != 6 or normalized[4] != "Q" or normalized[5] not in "1234":
        raise ValueError("quarter must use YYYYQ# format, for example 2026Q2")
    try:
        year = int(normalized[:4])
    except ValueError as exc:
        raise ValueError("quarter must use YYYYQ# format, for example 2026Q2") from exc
    return normalized, year, normalized[4:]


def _speaker_mapping(payload: Mapping[str, Any]) -> dict[int, tuple[str | None, str | None, str | None]]:
    result: dict[int, tuple[str | None, str | None, str | None]] = {}
    raw = payload.get("speaker_mapping")
    if not isinstance(raw, list):
        return result
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        index = item.get("speaker")
        data = item.get("speaker_data")
        if not isinstance(index, int) or not isinstance(data, Mapping):
            continue
        name = str(data.get("name") or "").strip() or None
        role = str(data.get("role") or "").strip() or None
        company = str(data.get("company") or "").strip() or None
        result[index] = (name, role, company)
    return result


def _turn_title(role: str | None, company: str | None) -> str | None:
    if role and company:
        return f"{role} | {company}"
    return role or company


@dataclass
class QuartrTranscriptSource:
    """Retrieve normalized edited Quartr earnings-call transcripts.

    V2 intentionally accepts only edited transcripts (Quartr typeId 22) because speaker
    identification, roles, and company affiliations are required to preserve the scanner's
    issuer-evidence / analyst-question provenance invariant. Raw typeId 15 transcripts are
    therefore not a silent fallback.
    """

    api_key: str
    metadata_transport: MetadataTransport = _default_metadata_transport
    file_transport: FileTransport = _default_file_transport
    base_url: str = "https://api.quartr.com/public/v3"
    provider_name: str = "quartr_edited"

    @property
    def headers(self) -> Mapping[str, str]:
        return {
            "User-Agent": "industry-bottleneck-scanner/0.1",
            "x-api-key": self.api_key,
        }

    def build_list_url(self, *, ticker: str) -> str:
        symbol = normalize_ticker(ticker)
        if not symbol:
            raise ValueError("ticker is required")
        query = urlencode(
            {
                "tickers": symbol,
                "typeIds": "22",
                "expand": "event",
                "limit": "100",
            }
        )
        return f"{self.base_url}/documents/transcripts?{query}"

    def fetch(self, *, ticker: str, quarter: str) -> EarningsCallTranscript | None:
        symbol = normalize_ticker(ticker)
        fiscal_quarter, year, period = _validate_quarter(quarter)
        payload = self.metadata_transport(self.build_list_url(ticker=symbol), self.headers)
        records = payload.get("data")
        if records in (None, []):
            return None
        if not isinstance(records, list):
            raise TranscriptProviderError("Quartr transcript list data field is not a list")

        matches: list[Mapping[str, Any]] = []
        for item in records:
            if not isinstance(item, Mapping):
                continue
            if item.get("typeId") != 22:
                continue
            event = item.get("event")
            if not isinstance(event, Mapping):
                continue
            if event.get("language") not in (None, "en"):
                continue
            if event.get("fiscalYear") != year or str(event.get("fiscalPeriod") or "").upper() != period:
                continue
            if not item.get("fileUrl"):
                continue
            matches.append(item)

        if not matches:
            return None
        matches.sort(key=lambda item: (str(item.get("updatedAt") or ""), int(item.get("id") or 0)), reverse=True)
        selected = matches[0]
        file_url = str(selected["fileUrl"])
        transcript_payload = self.file_transport(file_url)
        mapping = _speaker_mapping(transcript_payload)
        if not mapping:
            raise TranscriptProviderError(
                "Quartr edited transcript is missing speaker_mapping; refusing role-unsafe fallback"
            )

        transcript = transcript_payload.get("transcript")
        if not isinstance(transcript, Mapping):
            raise TranscriptProviderError("Quartr transcript file is missing transcript object")
        paragraphs = transcript.get("paragraphs")
        if not isinstance(paragraphs, list):
            raise TranscriptProviderError("Quartr transcript paragraphs field is not a list")

        turns: list[TranscriptTurn] = []
        for paragraph in paragraphs:
            if not isinstance(paragraph, Mapping):
                continue
            text = str(paragraph.get("text") or "").strip()
            if not text:
                continue
            speaker_index = paragraph.get("speaker")
            speaker_name: str | None = None
            speaker_role: str | None = None
            speaker_company: str | None = None
            if isinstance(speaker_index, int):
                speaker_name, speaker_role, speaker_company = mapping.get(speaker_index, (None, None, None))
            turns.append(
                TranscriptTurn(
                    speaker=speaker_name,
                    title=_turn_title(speaker_role, speaker_company),
                    text=text,
                )
            )

        if not turns:
            return None

        return EarningsCallTranscript(
            provider=self.provider_name,
            ticker=symbol,
            fiscal_quarter=fiscal_quarter,
            turns=tuple(turns),
            source_url=file_url,
        )
