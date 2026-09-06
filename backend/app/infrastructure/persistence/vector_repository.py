"""Vector validation shared by JSON-local and pgvector deployment persistence."""

import math


EMBEDDING_DIMENSION = 768


class VectorRepository:
    dimension = EMBEDDING_DIMENSION

    def validate(self, embedding: list[float] | None) -> list[float] | None:
        if embedding is None:
            return None
        if len(embedding) != self.dimension or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in embedding
        ):
            raise ValueError(f"Embedding must contain exactly {self.dimension} finite numeric values.")
        return [float(value) for value in embedding]

    def pgvector_literal(self, embedding: list[float]) -> str:
        values = self.validate(embedding)
        return "[" + ",".join(format(value, ".9g") for value in values or []) + "]"
