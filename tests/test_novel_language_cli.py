import json
from datetime import datetime, timezone

from industry_bottleneck_scanner import novel_language_cli
from industry_bottleneck_scanner.candidate_retrieval import RetrievalCandidate
from industry_bottleneck_scanner.models import Classification, SourceDocument
from industry_bottleneck_scanner.review_queue import FileReviewQueue, ReviewRecord


def _record(index: int) -> ReviewRecord:
    document = SourceDocument(
        document_id=f"doc-{index}",
        company_id=f"issuer-{index}",
        ticker=f"T{index}",
        document_type="earnings_call_turn",
        published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        text="Customer requirements are outpacing available production capacity.",
        classification=Classification(industry="Electrical Equipment"),
        speaker="CEO",
        source_section="qa",
    )
    candidate = RetrievalCandidate(
        document_id=document.document_id,
        scanner="scarcity",
        metric="capacity_constraint",
        evidence_text=document.text,
        methods=("semantic_local",),
        score=0.8,
        review_tier="review",
    )
    return ReviewRecord.from_candidate(candidate, document)


def test_novel_language_cli_writes_cross_company_candidates(tmp_path) -> None:
    queue_path = tmp_path / "review.json"
    FileReviewQueue(queue_path).enqueue(tuple(_record(index) for index in range(3)))
    output = tmp_path / "novel.json"

    assert novel_language_cli.main(
        [
            "--review-queue",
            str(queue_path),
            "--min-companies",
            "3",
            "--similarity-threshold",
            "0.9",
            "--output",
            str(output),
        ]
    ) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["pending_review_records"] == 3
    assert payload["cluster_count"] == 1
    assert payload["clusters"][0]["distinct_companies"] == 3
