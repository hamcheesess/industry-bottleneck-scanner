from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(_TOKEN_RE.findall(text.casefold()))


@dataclass(frozen=True)
class HashingNgramEncoder:
    """Dependency-free local encoder for cheap semantic-ish retrieval.

    This is not intended to replace a neural sentence encoder. It provides a deterministic,
    fully local fallback that improves recall for lexical variants without network access,
    model downloads, API keys, or paid inference. The public ``encode`` contract matches the
    semantic retriever's ``EmbeddingEncoder`` protocol, so a stronger local model can be
    swapped in later without changing the retrieval pipeline.
    """

    dimensions: int = 384
    max_ngram: int = 2

    def __post_init__(self) -> None:
        if self.dimensions <= 0:
            raise ValueError("dimensions must be positive")
        if self.max_ngram not in {1, 2, 3}:
            raise ValueError("max_ngram must be 1, 2, or 3")

    def _features(self, text: str) -> Counter[str]:
        tokens = _tokens(text)
        features: Counter[str] = Counter(tokens)
        for n in range(2, self.max_ngram + 1):
            features.update("_".join(tokens[index : index + n]) for index in range(len(tokens) - n + 1))
        return features

    def _index_and_sign(self, feature: str) -> tuple[int, float]:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big", signed=False)
        index = value % self.dimensions
        sign = -1.0 if value & 1 else 1.0
        return index, sign

    def encode(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        vectors: list[tuple[float, ...]] = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for feature, count in self._features(text).items():
                index, sign = self._index_and_sign(feature)
                vector[index] += sign * (1.0 + math.log(count))
            norm = math.sqrt(sum(value * value for value in vector))
            if norm:
                vector = [value / norm for value in vector]
            vectors.append(tuple(vector))
        return tuple(vectors)


class SentenceTransformerEncoder:
    """Optional local neural encoder with lazy dependency loading.

    Importing this module never downloads a model and never requires the optional package.
    A model is loaded only when this class is instantiated. Production callers should point
    ``model_name_or_path`` at an explicitly managed local model whenever offline operation is
    required.
    """

    def __init__(self, model_name_or_path: str, *, local_files_only: bool = True) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError(
                "SentenceTransformerEncoder requires the optional 'sentence-transformers' package"
            ) from exc

        self.model_name_or_path = model_name_or_path
        self.local_files_only = local_files_only
        self._model = SentenceTransformer(
            model_name_or_path,
            local_files_only=local_files_only,
        )

    def encode(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        vectors = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return tuple(tuple(float(value) for value in vector) for vector in vectors)
