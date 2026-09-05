from datetime import datetime, timezone

from industry_bottleneck_scanner.models import SourceDocument
from industry_bottleneck_scanner.semantic_retrieval import LocalSemanticRetriever, SemanticPrototype


class StubEncoder:
    def encode(self, texts):
        result = []
        for text in texts:
            lowered = text.casefold()
            if "insufficient" in lowered or "could have shipped" in lowered:
                result.append((1.0, 0.0))
            elif "higher prices" in lowered:
                result.append((0.0, 1.0))
            else:
                result.append((0.2, 0.2))
        return result


def make_document(text: str) -> SourceDocument:
    return SourceDocument(
        document_id="turn-1",
        company_id="issuer-1",
        ticker="TEST",
        document_type="earnings_call_turn",
        published_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
        text=text,
    )


def test_recovers_paraphrase_without_exact_phrase() -> None:
    retriever = LocalSemanticRetriever(
        StubEncoder(),
        prototypes=(
            SemanticPrototype(
                scanner="scarcity",
                metric="capacity_constraint",
                text="Available production capacity is insufficient to satisfy demand.",
            ),
        ),
        threshold=0.9,
    )

    candidates = retriever.retrieve(
        make_document("We could have shipped considerably more product if the equipment had been in place.")
    )

    assert len(candidates) == 1
    assert candidates[0].metric == "capacity_constraint"
    assert candidates[0].extraction_method == "semantic_local"


def test_ignores_low_similarity_text() -> None:
    retriever = LocalSemanticRetriever(
        StubEncoder(),
        prototypes=(
            SemanticPrototype(
                scanner="scarcity",
                metric="capacity_constraint",
                text="Available production capacity is insufficient to satisfy demand.",
            ),
        ),
        threshold=0.9,
    )

    assert retriever.retrieve(make_document("Routine administrative matters were discussed.")) == ()
