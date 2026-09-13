from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, time as datetime_time, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.request import Request, urlopen

from .disclosure_documents import DisclosureSection, PublicDisclosure
from .models import Classification
from .universe import normalize_cik

SEC_PROVIDER = "sec_edgar"
SEC_DISCLOSURE_FORMS = frozenset({"8-K", "10-Q", "10-K"})


class SecEdgarError(RuntimeError):
    """A bounded, retryable SEC transport or response-contract failure."""


@dataclass(frozen=True)
class SecIssuer:
    company_id: str
    cik: str
    ticker: str | None = None
    classification: Classification = Classification()

    def __post_init__(self) -> None:
        normalized_cik = normalize_cik(self.cik)
        if not self.company_id.strip():
            raise ValueError("SecIssuer.company_id is required")
        if normalized_cik is None:
            raise ValueError("SecIssuer.cik is required")
        object.__setattr__(self, "cik", normalized_cik)


@dataclass(frozen=True)
class SecFiling:
    accession_number: str
    form: str
    filing_date: date
    accepted_at: datetime
    primary_document: str
    primary_document_description: str | None = None

    @property
    def accession_compact(self) -> str:
        return self.accession_number.replace("-", "")


@dataclass(frozen=True)
class SecSubmittedDocument:
    sequence: str
    description: str
    filename: str
    document_type: str


@dataclass(frozen=True)
class SecCollectionDiagnostics:
    issuer_count: int
    filing_count: int
    disclosure_count: int
    skipped_unsupported_documents: int
    provider_requests: int
    cache_hits: int
    failed_issuer_count: int = 0
    failed_document_count: int = 0
    failures: tuple[str, ...] = ()


@dataclass(frozen=True)
class SecDisclosureCollection:
    disclosures: tuple[PublicDisclosure, ...]
    diagnostics: SecCollectionDiagnostics


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)


def _parse_sec_timestamp(value: object, fallback_date: date) -> datetime:
    text = str(value or "").strip()
    if text:
        normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise SecEdgarError(f"invalid SEC acceptance timestamp: {text}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return datetime.combine(fallback_date, datetime_time.min, tzinfo=timezone.utc)


def _columnar_rows(payload: Mapping[str, object]) -> tuple[dict[str, object], ...]:
    columns = {key: value for key, value in payload.items() if isinstance(value, list)}
    if not columns:
        return ()
    lengths = {len(value) for value in columns.values()}
    if len(lengths) != 1:
        raise SecEdgarError("SEC submissions columns have inconsistent lengths")
    row_count = lengths.pop()
    return tuple(
        {name: values[index] for name, values in columns.items()}
        for index in range(row_count)
    )


def _filing_from_row(row: Mapping[str, object]) -> SecFiling:
    accession = str(row.get("accessionNumber") or "").strip()
    form = str(row.get("form") or "").strip().upper()
    primary_document = str(row.get("primaryDocument") or "").strip()
    filing_date_text = str(row.get("filingDate") or "").strip()
    if not accession or not form or not primary_document or not filing_date_text:
        raise SecEdgarError("SEC filing row is missing required metadata")
    try:
        filing_date = date.fromisoformat(filing_date_text)
    except ValueError as exc:
        raise SecEdgarError(f"invalid SEC filing date: {filing_date_text}") from exc
    return SecFiling(
        accession_number=accession,
        form=form,
        filing_date=filing_date,
        accepted_at=_parse_sec_timestamp(row.get("acceptanceDateTime"), filing_date),
        primary_document=primary_document,
        primary_document_description=str(row.get("primaryDocDescription") or "").strip() or None,
    )


class _FilingIndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_row = False
        self._in_cell = False
        self._cell_text: list[str] = []
        self._cell_href: str | None = None
        self._cells: list[tuple[str, str | None]] = []
        self.documents: list[SecSubmittedDocument] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.casefold()
        if normalized == "tr":
            self._in_row = True
            self._cells = []
        elif self._in_row and normalized in {"td", "th"}:
            self._in_cell = True
            self._cell_text = []
            self._cell_href = None
        elif self._in_cell and normalized == "a":
            self._cell_href = dict(attrs).get("href")

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if self._in_cell and normalized in {"td", "th"}:
            self._cells.append((" ".join("".join(self._cell_text).split()), self._cell_href))
            self._in_cell = False
        elif self._in_row and normalized == "tr":
            self._finish_row()
            self._in_row = False

    def _finish_row(self) -> None:
        if len(self._cells) < 4:
            return
        sequence, description, document, document_type = self._cells[:4]
        href = document[1] or document[0]
        viewer_document = parse_qs(urlparse(href).query).get("doc", [""])[0]
        filename = Path(viewer_document or urlparse(href).path).name or document[0]
        if not filename or document_type[0].casefold() == "type":
            return
        self.documents.append(
            SecSubmittedDocument(
                sequence=sequence[0],
                description=description[0],
                filename=filename,
                document_type=document_type[0].upper(),
            )
        )


class _ReadableHtmlParser(HTMLParser):
    _block_tags = frozenset(
        {"address", "article", "blockquote", "br", "caption", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "p", "section", "td", "th", "tr"}
    )
    _ignored_tags = frozenset({"head", "script", "style", "svg", "ix:header"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._buffer: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.casefold()
        if normalized in self._ignored_tags:
            self._ignored_depth += 1
        elif self._ignored_depth == 0 and normalized in self._block_tags:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if normalized in self._ignored_tags and self._ignored_depth:
            self._ignored_depth -= 1
        elif self._ignored_depth == 0 and normalized in self._block_tags:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0:
            self._buffer.append(data)

    def close(self) -> None:
        super().close()
        self._flush()

    def _flush(self) -> None:
        text = " ".join("".join(self._buffer).split())
        self._buffer = []
        if text and (not self.blocks or text != self.blocks[-1]):
            self.blocks.append(text)


def html_to_sections(content: bytes, *, max_section_characters: int = 20_000) -> tuple[DisclosureSection, ...]:
    if max_section_characters < 1:
        raise ValueError("max_section_characters must be positive")
    parser = _ReadableHtmlParser()
    parser.feed(content.decode("utf-8", errors="replace"))
    parser.close()
    sections: list[DisclosureSection] = []
    current: list[str] = []
    current_size = 0
    blocks: list[str] = []
    for block in parser.blocks:
        remaining = block
        while len(remaining) > max_section_characters:
            split_at = remaining.rfind(" ", 0, max_section_characters + 1)
            if split_at < 1:
                split_at = max_section_characters
            blocks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()
        if remaining:
            blocks.append(remaining)
    for block in blocks:
        block_size = len(block) + (2 if current else 0)
        if current and current_size + block_size > max_section_characters:
            sections.append(
                DisclosureSection(
                    section_id=f"section-{len(sections) + 1:04d}",
                    text="\n\n".join(current),
                )
            )
            current = []
            current_size = 0
        current.append(block)
        current_size += block_size
    if current:
        sections.append(
            DisclosureSection(
                section_id=f"section-{len(sections) + 1:04d}",
                text="\n\n".join(current),
            )
        )
    return tuple(sections)


def _is_html_or_text(filename: str) -> bool:
    return Path(filename.casefold()).suffix in {".htm", ".html", ".txt"}


class SecEdgarClient:
    """Cache-first public EDGAR adapter that enforces declared fair-access identity."""

    submissions_base_url = "https://data.sec.gov/submissions/"
    archives_base_url = "https://www.sec.gov/Archives/edgar/data/"
    allowed_hosts = frozenset({"data.sec.gov", "www.sec.gov"})

    def __init__(
        self,
        *,
        user_agent: str,
        cache_dir: Path,
        request_interval_seconds: float = 0.2,
        max_attempts: int = 3,
        transport: Callable[[Request], bytes] | None = None,
    ) -> None:
        declared_identity = user_agent.strip()
        if "@" not in declared_identity or " " not in declared_identity:
            raise ValueError("SEC user agent must declare an organization and contact email")
        if request_interval_seconds < 0.1:
            raise ValueError("SEC request interval must remain at least 0.1 seconds")
        if max_attempts < 1:
            raise ValueError("SEC max_attempts must be at least 1")
        self._user_agent = declared_identity
        self._cache_dir = cache_dir
        self._request_interval_seconds = request_interval_seconds
        self._transport = transport or self._open_request
        self._max_attempts = max_attempts
        self._last_request_at: float | None = None
        self.provider_requests = 0
        self.cache_hits = 0

    @staticmethod
    def _open_request(request: Request) -> bytes:
        try:
            with urlopen(request, timeout=60) as response:  # noqa: S310 - host checked before transport
                return response.read()
        except HTTPError as exc:
            detail = " (fair-access identity or pacing may be rejected)" if exc.code in {403, 429} else ""
            raise SecEdgarError(f"SEC EDGAR HTTP {exc.code}{detail}") from exc
        except (URLError, TimeoutError) as exc:
            reason = getattr(exc, "reason", str(exc))
            raise SecEdgarError(f"SEC EDGAR transport error: {reason}") from exc

    def _cache_path(self, url: str) -> Path:
        parsed = urlparse(url)
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        filename = Path(parsed.path).name or "index"
        return self._cache_dir / parsed.netloc / f"{digest}-{filename}"

    def _get(self, url: str) -> bytes:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in self.allowed_hosts:
            raise SecEdgarError("SEC adapter rejected an unexpected provider URL")
        cache_path = self._cache_path(url)
        if cache_path.exists():
            self.cache_hits += 1
            return cache_path.read_bytes()
        if self._last_request_at is not None:
            wait = self._request_interval_seconds - (time.monotonic() - self._last_request_at)
            if wait > 0:
                time.sleep(wait)
        request = Request(
            url,
            headers={
                "User-Agent": self._user_agent,
                "Accept": "application/json,text/html,text/plain;q=0.9,*/*;q=0.1",
            },
        )
        content = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                content = self._transport(request)
                break
            except SecEdgarError as exc:
                message = str(exc).casefold()
                retryable = (
                    "transport error" in message
                    or "http 429" in message
                    or any(f"http {code}" in message for code in range(500, 600))
                )
                if not retryable or attempt == self._max_attempts:
                    raise SecEdgarError(f"{url}: {exc}") from exc
                time.sleep(max(self._request_interval_seconds, float(2 ** (attempt - 1))))
        if content is None:  # pragma: no cover - loop either returns content or raises
            raise SecEdgarError(f"{url}: SEC transport produced no response")
        self._last_request_at = time.monotonic()
        self.provider_requests += 1
        _atomic_write(cache_path, content)
        return content

    def _json(self, url: str) -> Mapping[str, object]:
        try:
            payload = json.loads(self._get(url))
        except json.JSONDecodeError as exc:
            raise SecEdgarError("SEC EDGAR returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise SecEdgarError("SEC EDGAR JSON root must be an object")
        return payload

    def filings(
        self,
        *,
        cik: str,
        since: date,
        as_of: datetime,
        forms: Iterable[str] = SEC_DISCLOSURE_FORMS,
    ) -> tuple[SecFiling, ...]:
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        normalized_cik = normalize_cik(cik)
        if normalized_cik is None:
            raise ValueError("CIK is required")
        allowed_forms = frozenset(form.strip().upper() for form in forms)
        if not allowed_forms or not allowed_forms <= SEC_DISCLOSURE_FORMS:
            raise ValueError("forms must be a non-empty subset of 8-K, 10-Q, and 10-K")

        root = self._json(f"{self.submissions_base_url}CIK{normalized_cik}.json")
        filings_payload = root.get("filings")
        if not isinstance(filings_payload, dict):
            raise SecEdgarError("SEC submissions response has no filings object")
        recent = filings_payload.get("recent")
        if not isinstance(recent, dict):
            raise SecEdgarError("SEC submissions response has no recent filings")
        rows = list(_columnar_rows(recent))

        additional_files = filings_payload.get("files") or []
        if not isinstance(additional_files, list):
            raise SecEdgarError("SEC submissions additional files must be a list")
        for item in additional_files:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            filing_from = str(item.get("filingFrom") or "").strip()
            filing_to = str(item.get("filingTo") or "").strip()
            if not name or not filing_from or not filing_to:
                continue
            if date.fromisoformat(filing_to) < since or date.fromisoformat(filing_from) > as_of.date():
                continue
            rows.extend(_columnar_rows(self._json(urljoin(self.submissions_base_url, name))))

        selected: dict[str, SecFiling] = {}
        for row in rows:
            form = str(row.get("form") or "").strip().upper()
            filing_date_text = str(row.get("filingDate") or "").strip()
            if form not in allowed_forms or not filing_date_text:
                continue
            filing_date = date.fromisoformat(filing_date_text)
            if not since <= filing_date <= as_of.date():
                continue
            filing = _filing_from_row(row)
            if filing.accepted_at > as_of.astimezone(timezone.utc):
                continue
            selected[filing.accession_number] = filing
        return tuple(sorted(selected.values(), key=lambda item: (item.accepted_at, item.accession_number)))

    def archive_directory_url(self, cik: str, filing: SecFiling) -> str:
        normalized_cik = normalize_cik(cik)
        if normalized_cik is None:
            raise ValueError("CIK is required")
        return f"{self.archives_base_url}{int(normalized_cik)}/{filing.accession_compact}/"

    def submitted_documents(self, *, cik: str, filing: SecFiling) -> tuple[SecSubmittedDocument, ...]:
        directory_url = self.archive_directory_url(cik, filing)
        index_url = f"{directory_url}{filing.accession_number}-index.htm"
        parser = _FilingIndexParser()
        parser.feed(self._get(index_url).decode("utf-8", errors="replace"))
        parser.close()
        return tuple(parser.documents)

    def document_content(self, *, cik: str, filing: SecFiling, filename: str) -> tuple[str, bytes]:
        safe_filename = Path(filename).name
        if safe_filename != filename or not safe_filename:
            raise SecEdgarError("SEC filing document filename is unsafe")
        url = urljoin(self.archive_directory_url(cik, filing), safe_filename)
        return url, self._get(url)


def _documents_to_collect(
    filing: SecFiling,
    submitted: Sequence[SecSubmittedDocument],
) -> tuple[SecSubmittedDocument, ...]:
    documents: list[SecSubmittedDocument] = [
        SecSubmittedDocument(
            sequence="1",
            description=filing.primary_document_description or filing.form,
            filename=filing.primary_document,
            document_type=filing.form,
        )
    ]
    if filing.form == "8-K":
        documents.extend(item for item in submitted if item.document_type.startswith("EX-99"))
    unique: dict[str, SecSubmittedDocument] = {}
    for item in documents:
        unique.setdefault(item.filename, item)
    return tuple(unique.values())


def collect_sec_disclosures(
    client: SecEdgarClient,
    *,
    issuers: Iterable[SecIssuer],
    since: date,
    as_of: datetime,
    retrieved_at: datetime | None = None,
) -> SecDisclosureCollection:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    retrieval_time = retrieved_at or datetime.now(timezone.utc)
    if retrieval_time.tzinfo is None:
        raise ValueError("retrieved_at must be timezone-aware")
    issuer_items = tuple(issuers)
    disclosures: list[PublicDisclosure] = []
    filing_count = 0
    skipped = 0
    failed_issuers: set[str] = set()
    failed_documents = 0
    failures: list[str] = []
    for issuer in issuer_items:
        try:
            filings = client.filings(cik=issuer.cik, since=since, as_of=as_of)
        except SecEdgarError as exc:
            failed_issuers.add(issuer.company_id)
            failures.append(f"issuer:{issuer.company_id}:{exc}")
            continue
        filing_count += len(filings)
        for filing in filings:
            submitted: tuple[SecSubmittedDocument, ...] = ()
            if filing.form == "8-K":
                try:
                    submitted = client.submitted_documents(cik=issuer.cik, filing=filing)
                except SecEdgarError as exc:
                    failed_documents += 1
                    failures.append(
                        f"filing-index:{issuer.company_id}:{filing.accession_number}:{exc}"
                    )
            for document in _documents_to_collect(filing, submitted):
                if not _is_html_or_text(document.filename):
                    skipped += 1
                    continue
                try:
                    source_url, content = client.document_content(
                        cik=issuer.cik,
                        filing=filing,
                        filename=document.filename,
                    )
                except SecEdgarError as exc:
                    failed_documents += 1
                    failures.append(
                        f"document:{issuer.company_id}:{filing.accession_number}:"
                        f"{document.filename}:{exc}"
                    )
                    continue
                sections = html_to_sections(content)
                if not sections:
                    skipped += 1
                    continue
                if filing.form == "8-K" and document.document_type.startswith("EX-99"):
                    document_type = "sec_8k_exhibit"
                else:
                    document_type = "sec_" + filing.form.casefold().replace("-", "")
                disclosures.append(
                    PublicDisclosure(
                        provider=SEC_PROVIDER,
                        provider_document_id=f"{filing.accession_number}:{document.filename}",
                        company_id=issuer.company_id,
                        ticker=issuer.ticker,
                        document_type=document_type,
                        published_at=filing.accepted_at,
                        retrieved_at=retrieval_time,
                        source_url=source_url,
                        classification=issuer.classification,
                        sections=tuple(
                            DisclosureSection(
                                section_id=section.section_id,
                                text=section.text,
                                source_section=f"{document.filename}:{section.section_id}",
                            )
                            for section in sections
                        ),
                    )
                )
    return SecDisclosureCollection(
        disclosures=tuple(disclosures),
        diagnostics=SecCollectionDiagnostics(
            issuer_count=len(issuer_items),
            filing_count=filing_count,
            disclosure_count=len(disclosures),
            skipped_unsupported_documents=skipped,
            provider_requests=client.provider_requests,
            cache_hits=client.cache_hits,
            failed_issuer_count=len(failed_issuers),
            failed_document_count=failed_documents,
            failures=tuple(failures),
        ),
    )
