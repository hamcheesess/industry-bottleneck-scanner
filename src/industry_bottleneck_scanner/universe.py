from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date
from io import StringIO
from typing import Iterable, Mapping

CANONICAL_UNIVERSE_ID = "russell_3000"


def normalize_ticker(value: str) -> str:
    return value.strip().upper().replace(".", "-")


def normalize_cik(value: str | None) -> str | None:
    if value is None:
        return None
    digits = "".join(character for character in value if character.isdigit())
    if not digits:
        return None
    return digits.zfill(10)


def _stable_security_id(ticker: str, exchange: str | None) -> str:
    payload = f"{exchange or ''}|{ticker}".encode("utf-8")
    return "security-" + hashlib.sha256(payload).hexdigest()[:16]


@dataclass(frozen=True)
class UniverseMember:
    security_id: str
    issuer_id: str
    ticker: str
    company_name: str
    exchange: str | None = None
    cik: str | None = None
    memberships: tuple[str, ...] = (CANONICAL_UNIVERSE_ID,)
    active: bool = True

    @property
    def sec_resolvable(self) -> bool:
        return self.cik is not None


@dataclass(frozen=True)
class UniverseSnapshot:
    universe_id: str
    as_of: date
    source: str
    members: tuple[UniverseMember, ...]

    @property
    def active_members(self) -> tuple[UniverseMember, ...]:
        return tuple(member for member in self.members if member.active)

    @property
    def sec_resolvable_members(self) -> tuple[UniverseMember, ...]:
        return tuple(member for member in self.active_members if member.sec_resolvable)

    @property
    def unresolved_members(self) -> tuple[UniverseMember, ...]:
        return tuple(member for member in self.active_members if not member.sec_resolvable)


def build_snapshot(
    rows: Iterable[Mapping[str, str]],
    *,
    as_of: date,
    source: str,
    universe_id: str = CANONICAL_UNIVERSE_ID,
) -> UniverseSnapshot:
    members: list[UniverseMember] = []
    seen_security_ids: set[str] = set()

    for row_number, row in enumerate(rows, start=2):
        ticker = normalize_ticker(row.get("ticker", ""))
        company_name = row.get("company_name", "").strip()
        if not ticker:
            raise ValueError(f"row {row_number}: ticker is required")
        if not company_name:
            raise ValueError(f"row {row_number}: company_name is required")

        exchange = row.get("exchange", "").strip().upper() or None
        cik = normalize_cik(row.get("cik"))
        security_id = row.get("security_id", "").strip() or _stable_security_id(ticker, exchange)
        if security_id in seen_security_ids:
            raise ValueError(f"row {row_number}: duplicate security_id {security_id!r}")
        seen_security_ids.add(security_id)

        issuer_id = row.get("issuer_id", "").strip()
        if not issuer_id:
            issuer_id = f"cik-{cik}" if cik else f"ticker-{ticker}"

        extra_memberships = tuple(
            item.strip()
            for item in row.get("memberships", "").split(";")
            if item.strip()
        )
        memberships = tuple(dict.fromkeys((universe_id, *extra_memberships)))
        active_value = row.get("active", "true").strip().casefold()
        active = active_value not in {"0", "false", "no", "inactive"}

        members.append(
            UniverseMember(
                security_id=security_id,
                issuer_id=issuer_id,
                ticker=ticker,
                company_name=company_name,
                exchange=exchange,
                cik=cik,
                memberships=memberships,
                active=active,
            )
        )

    if not members:
        raise ValueError("universe snapshot must contain at least one member")

    return UniverseSnapshot(
        universe_id=universe_id,
        as_of=as_of,
        source=source,
        members=tuple(members),
    )


def load_snapshot_csv(
    text: str,
    *,
    as_of: date,
    source: str,
    universe_id: str = CANONICAL_UNIVERSE_ID,
) -> UniverseSnapshot:
    reader = csv.DictReader(StringIO(text))
    fieldnames = set(reader.fieldnames or ())
    required = {"ticker", "company_name"}
    missing = required - fieldnames
    if missing:
        raise ValueError(f"universe CSV missing required columns: {sorted(missing)}")
    return build_snapshot(
        reader,
        as_of=as_of,
        source=source,
        universe_id=universe_id,
    )
