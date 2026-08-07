from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .embedding_adapters import HashingNgramEncoder
from .novel_language import cluster_pending_review_language
from .review_queue import FileReviewQueue


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Surface repeated semantic-only language across independent companies."
    )
    parser.add_argument("--review-queue", type=Path, default=Path("var/review/semantic.json"))
    parser.add_argument("--min-companies", type=int, default=3)
    parser.add_argument("--similarity-threshold", type=float, default=0.72)
    parser.add_argument("--output", type=Path, default=Path("var/review/novel-language.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.min_companies < 2:
        raise SystemExit("--min-companies must be at least 2")
    if not 0.0 <= args.similarity_threshold <= 1.0:
        raise SystemExit("--similarity-threshold must be between 0 and 1")

    records = FileReviewQueue(args.review_queue).load()
    clusters = cluster_pending_review_language(
        records,
        encoder=HashingNgramEncoder(),
        similarity_threshold=args.similarity_threshold,
        min_companies=args.min_companies,
    )
    payload = {
        "pending_review_records": sum(record.status == "pending" for record in records),
        "cluster_count": len(clusters),
        "clusters": [asdict(cluster) | {"distinct_companies": cluster.distinct_companies} for cluster in clusters],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"pending_review_records={payload['pending_review_records']} "
        f"novel_language_clusters={len(clusters)}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
