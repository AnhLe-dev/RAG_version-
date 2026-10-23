from collections.abc import Sequence
from math import isfinite

from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
)

from app.rag.models import RetrievedChunk


def search_dense(
    client: QdrantClient,
    *,
    collection_name: str,
    query_vector: Sequence[float],
    access_scope: str,
    source_id: str,
    source_version: str,
    limit: int,
    expected_dimensions: int,
) -> tuple[RetrievedChunk, ...]:
    """Find chunks from one authorized knowledge source."""

    normalized_scope = access_scope.strip()
    normalized_source_id = source_id.strip()
    normalized_source_version = source_version.strip()

    if not normalized_scope:
        raise ValueError(
            "Access scope must not be empty"
        )

    if not normalized_source_id:
        raise ValueError(
            "Source ID must not be empty"
        )

    if not normalized_source_version:
        raise ValueError(
            "Source version must not be empty"
        )

    if limit <= 0:
        raise ValueError(
            "Retrieval limit must be greater than zero"
        )

    if len(query_vector) != expected_dimensions:
        raise ValueError(
            "Query vector has an unexpected dimension: "
            f"expected={expected_dimensions}, "
            f"actual={len(query_vector)}"
        )

    if not all(isfinite(value) for value in query_vector):
        raise ValueError(
            "Query vector contains a non-finite value"
        )

    query_response = client.query_points(
        collection_name=collection_name,
        query=list(query_vector),
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="access_scope",
                    match=MatchValue(
                        value=normalized_scope
                    ),
                ),
                FieldCondition(
                    key="source_id",
                    match=MatchValue(
                        value=normalized_source_id
                    ),
                ),
                FieldCondition(
                    key="source_version",
                    match=MatchValue(
                        value=normalized_source_version
                    ),
                ),
            ]
        ),
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    points = query_response.points

    results: list[RetrievedChunk] = []

    for point in points:
        if point.payload is None:
            raise ValueError(
                f"Qdrant point {point.id} has no payload"
            )

        results.append(
            RetrievedChunk.model_validate({
                **point.payload,
                "score": point.score,
            })
        )

    return tuple(results)