from __future__ import annotations

from dataclasses import dataclass

from .models import ScannerCategory, SignalDirection


@dataclass(frozen=True)
class SignalPattern:
    scanner: ScannerCategory
    metric: str
    phrases: tuple[str, ...]
    direction: SignalDirection
    base_confidence: float = 0.75


# Phase 1 vocabulary is intentionally explicit and auditable.  The categories are
# logical dimensions; one sentence can emit several metrics when it contains
# independent evidence (for example record backlog + elevated lead times).
DEFAULT_PATTERNS: tuple[SignalPattern, ...] = (
    # ------------------------------------------------------------------
    # CAPEX — focus on revisions / concrete expansion actions, not merely
    # the existence of large capital expenditure.
    # ------------------------------------------------------------------
    SignalPattern(
        scanner="capex",
        metric="capex_revision_up",
        phrases=(
            "raising capital expenditure",
            "raised capital expenditure",
            "raising capex guidance",
            "raised capex guidance",
            "capital plan increased",
            "increased capital plan",
            "investment plan increased",
            "increased investment plan",
            "accelerating investment",
        ),
        direction="strengthening",
        base_confidence=0.85,
    ),
    SignalPattern(
        scanner="capex",
        metric="capex_revision_down",
        phrases=(
            "lowering capital expenditure",
            "lowered capital expenditure",
            "lowering capex guidance",
            "lowered capex guidance",
            "capital plan decreased",
            "reduced capital plan",
            "cutting investment",
            "reduced investment plan",
        ),
        direction="weakening",
        base_confidence=0.85,
    ),
    SignalPattern(
        scanner="capex",
        metric="capacity_expansion",
        phrases=(
            "capacity expansion",
            "expanding capacity",
            "new facility",
            "new production line",
            "expansion project",
            "greenfield project",
            "brownfield expansion",
            "adding capacity",
        ),
        direction="strengthening",
    ),
    # ------------------------------------------------------------------
    # DEMAND — separate backlog, bookings, book-to-bill and forward
    # capacity commitments so acceleration can be inspected by metric.
    # ------------------------------------------------------------------
    SignalPattern(
        scanner="demand",
        metric="backlog_strength",
        phrases=(
            "record backlog",
            "backlog increased",
            "backlog grew",
            "backlog growth",
            "backlog remains strong",
            "backlog remains elevated",
        ),
        direction="strengthening",
        base_confidence=0.85,
    ),
    SignalPattern(
        scanner="demand",
        metric="backlog_weakness",
        phrases=(
            "backlog decreased",
            "backlog declined",
            "backlog contracted",
            "backlog normalization",
        ),
        direction="weakening",
        base_confidence=0.85,
    ),
    SignalPattern(
        scanner="demand",
        metric="bookings_strength",
        phrases=(
            "record bookings",
            "bookings increased",
            "bookings grew",
            "strong bookings",
            "order intake increased",
            "record orders",
        ),
        direction="strengthening",
        base_confidence=0.8,
    ),
    SignalPattern(
        scanner="demand",
        metric="book_to_bill_above_one",
        phrases=(
            "book-to-bill above 1",
            "book to bill above 1",
            "book-to-bill greater than 1",
            "book to bill greater than 1",
            "book-to-bill exceeded 1",
        ),
        direction="strengthening",
        base_confidence=0.9,
    ),
    SignalPattern(
        scanner="demand",
        metric="forward_capacity_commitment",
        phrases=(
            "customers are reserving capacity",
            "customers reserving capacity",
            "reserve capacity",
            "reserved capacity",
            "secured capacity",
            "capacity reservation",
            "long-term supply agreement",
            "long term supply agreement",
            "multi-year agreement",
            "multi year agreement",
        ),
        direction="strengthening",
        base_confidence=0.8,
    ),
    # ------------------------------------------------------------------
    # SCARCITY — distinguish the physical mechanism of the bottleneck.
    # ------------------------------------------------------------------
    SignalPattern(
        scanner="scarcity",
        metric="lead_time_pressure",
        phrases=(
            "lead times increased",
            "lead time increased",
            "lead times extended",
            "lead time extended",
            "lead times remain elevated",
            "lead time remains elevated",
            "long lead time",
            "long lead times",
        ),
        direction="strengthening",
        base_confidence=0.9,
    ),
    SignalPattern(
        scanner="scarcity",
        metric="capacity_constraint",
        phrases=(
            "capacity constrained",
            "capacity constraint",
            "capacity limitation",
            "capacity limitations",
            "capacity remains tight",
            "unable to meet demand",
        ),
        direction="strengthening",
        base_confidence=0.9,
    ),
    SignalPattern(
        scanner="scarcity",
        metric="supply_tightness",
        phrases=(
            "supply remains tight",
            "supply is tight",
            "supply-demand imbalance",
            "supply demand imbalance",
            "limited availability",
            "shortage",
            "supply shortage",
        ),
        direction="strengthening",
        base_confidence=0.85,
    ),
    SignalPattern(
        scanner="scarcity",
        metric="allocation",
        phrases=(
            "on allocation",
            "under allocation",
            "product allocation",
            "supply allocation",
            "allocation remains",
        ),
        direction="strengthening",
        base_confidence=0.85,
    ),
    SignalPattern(
        scanner="scarcity",
        metric="sold_out_capacity",
        phrases=(
            "sold out through",
            "capacity sold out",
            "fully booked through",
            "production sold out",
        ),
        direction="strengthening",
        base_confidence=0.95,
    ),
    SignalPattern(
        scanner="scarcity",
        metric="qualification_barrier",
        phrases=(
            "qualification takes",
            "qualification process takes",
            "qualification cycle",
            "customer qualification",
            "qualification period",
            "certification takes",
        ),
        direction="strengthening",
        base_confidence=0.75,
    ),
    # ------------------------------------------------------------------
    # PRICING — evidence that demand/scarcity is translating into economics.
    # ------------------------------------------------------------------
    SignalPattern(
        scanner="pricing",
        metric="pricing_power",
        phrases=(
            "pricing remains strong",
            "strong pricing",
            "pricing power",
            "price increase",
            "price increases",
            "raised prices",
        ),
        direction="strengthening",
        base_confidence=0.85,
    ),
    SignalPattern(
        scanner="pricing",
        metric="contract_repricing",
        phrases=(
            "contract repricing",
            "repriced contracts",
            "pricing escalator",
            "price escalation clause",
            "take-or-pay",
            "take or pay",
            "reservation fee",
        ),
        direction="strengthening",
        base_confidence=0.8,
    ),
    SignalPattern(
        scanner="pricing",
        metric="margin_from_pricing",
        phrases=(
            "margin expansion from pricing",
            "margin improvement from pricing",
            "favorable price cost",
            "favourable price cost",
            "price cost positive",
            "pricing more than offset cost",
        ),
        direction="strengthening",
        base_confidence=0.9,
    ),
    SignalPattern(
        scanner="pricing",
        metric="pricing_weakness",
        phrases=(
            "pricing declined",
            "pricing decreased",
            "price decreases",
            "price pressure",
            "pricing pressure",
        ),
        direction="weakening",
        base_confidence=0.8,
    ),
)
