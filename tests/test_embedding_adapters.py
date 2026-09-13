import pytest

from industry_bottleneck_scanner.embedding_adapters import HashingNgramEncoder


def _cosine(left, right):
    return sum(a * b for a, b in zip(left, right))


def test_hashing_encoder_is_deterministic_and_normalized() -> None:
    encoder = HashingNgramEncoder(dimensions=128)
    first, second = encoder.encode(["capacity remains tight", "capacity remains tight"])

    assert first == second
    assert sum(value * value for value in first) == pytest.approx(1.0)


def test_hashing_encoder_scores_related_text_above_unrelated_text() -> None:
    encoder = HashingNgramEncoder(dimensions=512)
    prototype, related, unrelated = encoder.encode(
        [
            "customers are reserving future production capacity",
            "customers reserved production capacity for future delivery",
            "the company changed its corporate headquarters",
        ]
    )

    assert _cosine(prototype, related) > _cosine(prototype, unrelated)
