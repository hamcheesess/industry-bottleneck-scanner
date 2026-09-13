from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .models import AtomicSignal


@dataclass(frozen=True)
class SignalDiagnostics:
    total_signals: int
    active_strengthening: int
    distinct_companies: int
    distinct_metrics: int
    unclassified_signals: int
    prepared_signals: int
    qa_signals: int
    unknown_section_signals: int
    semantic_only_signals: int
    top_company_share: float
    company_signal_counts: tuple[tuple[str, int], ...]
    metric_signal_counts: tuple[tuple[str, int], ...]
    extraction_method_counts: tuple[tuple[str, int], ...]


def _active(signal: AtomicSignal) -> bool:
    return signal.direction == "strengthening" and not signal.negated and not signal.resolved


def summarize_signal_diagnostics(signals: tuple[AtomicSignal, ...]) -> SignalDiagnostics:
    """Emit simple quality diagnostics without changing research trigger semantics."""

    active = tuple(signal for signal in signals if _active(signal))
    company_counts = Counter(signal.company_id for signal in active)
    metric_counts = Counter(signal.metric for signal in active)
    method_counts = Counter(signal.extraction_method for signal in active)
    top_company_count = max(company_counts.values(), default=0)
    top_company_share = top_company_count / len(active) if active else 0.0

    return SignalDiagnostics(
        total_signals=len(signals),
        active_strengthening=len(active),
        distinct_companies=len(company_counts),
        distinct_metrics=len(metric_counts),
        unclassified_signals=sum(
            not (
                signal.classification.subindustry
                or signal.classification.industry
                or signal.classification.sector
            )
            for signal in active
        ),
        prepared_signals=sum(signal.source_section == "prepared" for signal in active),
        qa_signals=sum(signal.source_section == "qa" for signal in active),
        unknown_section_signals=sum(signal.source_section not in {"prepared", "qa"} for signal in active),
        semantic_only_signals=sum(
            signal.extraction_method == "semantic_local" for signal in active
        ),
        top_company_share=top_company_share,
        company_signal_counts=tuple(sorted(company_counts.items(), key=lambda item: (-item[1], item[0]))),
        metric_signal_counts=tuple(sorted(metric_counts.items(), key=lambda item: (-item[1], item[0]))),
        extraction_method_counts=tuple(sorted(method_counts.items(), key=lambda item: (-item[1], item[0]))),
    )
