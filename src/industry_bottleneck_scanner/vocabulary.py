from __future__ import annotations

from dataclasses import dataclass

from .models import ScannerCategory, SignalDirection


@dataclass(frozen=True)
class SignalPattern:
    scanner: ScannerCategory
    metric: str
    phrases: tuple[str, ...]
    direction: SignalDirection


DEFAULT_PATTERNS: tuple[SignalPattern, ...] = (
    SignalPattern(
        scanner="capex",
        metric="capacity_expansion",
        phrases=(
            "capacity expansion",
            "new facility",
            "expansion project",
            "capital plan increased",
            "raising capital expenditure",
            "increased investment",
        ),
        direction="strengthening",
    ),
    SignalPattern(
        scanner="demand",
        metric="backlog",
        phrases=(
            "record backlog",
            "record bookings",
            "book-to-bill above 1",
            "customers are reserving capacity",
            "secured capacity",
        ),
        direction="strengthening",
    ),
    SignalPattern(
        scanner="scarcity",
        metric="supply_constraint",
        phrases=(
            "capacity constrained",
            "lead times increased",
            "lead times remain elevated",
            "supply remains tight",
            "unable to meet demand",
            "sold out through",
            "limited availability",
            "allocation",
            "shortage",
        ),
        direction="strengthening",
    ),
    SignalPattern(
        scanner="pricing",
        metric="pricing_power",
        phrases=(
            "pricing remains strong",
            "price increase",
            "contract repricing",
            "favorable price cost",
            "margin expansion from pricing",
        ),
        direction="strengthening",
    ),
)
