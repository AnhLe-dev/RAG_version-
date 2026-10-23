from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from app.core.config import Settings
from app.rag.models import DocumentChunk


def create_qdrant_client(
    settings: Settings,
) -> QdrantClient:
    """Create a Qdrant Cloud client."""

    return QdrantClient(
        url=settings.qdrant_cloud_url,
        api_key=(
            settings.qdrant_cloud_api_key.get_secret_value()
        ),
        timeout=30,
    )




def _create_point(
    chunk: DocumentChunk,
    vector: Sequence[float],
) -> PointStruct:
    """Convert one chunk and vector into a Qdrant point."""

    point_id = str(
        uuid5(NAMESPACE_URL, chunk.chunk_id)
    )

    return PointStruct(
        id=point_id,
        vector=list(vector),
        payload={
            "chunk_id": chunk.chunk_id,
            "source_id": chunk.source_id,
            "source_version": chunk.source_version,
            "source_checksum_sha256": (
                chunk.source_checksum_sha256
            ),
            "text": chunk.text,
            "article_number": chunk.article_number,
            "structure_path": list(
                chunk.structure_path
            ),
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "source_spans": [
                span.model_dump(mode="json")
                for span in chunk.source_spans
            ],
            "parent_chunk_id": (
                chunk.parent_chunk_id
            ),
            "access_scope": chunk.access_scope,
        },
    )


def upsert_chunks(
    client: QdrantClient,
    *,
    collection_name: str,
    chunks: tuple[DocumentChunk, ...],
    vectors: tuple[tuple[float, ...], ...],
    batch_size: int = 64,
) -> int:
    """Upload chunks and vectors to Qdrant."""

    if len(chunks) != len(vectors):
        raise ValueError(
            "Chunk count does not match vector count"
        )

    uploaded_count = 0

    for start in range(0, len(chunks), batch_size):
        batch_chunks = chunks[
            start:start + batch_size
        ]
        batch_vectors = vectors[
            start:start + batch_size
        ]

        points = [
            _create_point(chunk, vector)
            for chunk, vector in zip(
                batch_chunks,
                batch_vectors,
                strict=True,
            )
        ]

        client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True,
        )

        uploaded_count += len(points)

    return uploaded_count

def ensure_payload_index(
    client: QdrantClient,
    *,
    collection_name: str,
    field_name: str,
    field_schema: PayloadSchemaType,
) -> None:
    """Create or validate one payload index."""

    collection = client.get_collection(
        collection_name
    )

    existing_index = collection.payload_schema.get(
        field_name
    )

    if existing_index is None:
        client.create_payload_index(
            collection_name=collection_name,
            field_name=field_name,
            field_schema=field_schema,
            wait=True,
        )
        return

    if existing_index.data_type != field_schema:
        raise ValueError(
            "Unexpected Qdrant payload index type: "
            f"field={field_name}, "
            f"expected={field_schema.value}, "
            f"actual={existing_index.data_type.value}"
        )


def ensure_collection(
    client: QdrantClient,
    *,
    collection_name: str,
    vector_size: int,
) -> None:
    """Create or validate the collection and its indexes."""

    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )

    collection = client.get_collection(
        collection_name
    )

    vector_config = collection.config.params.vectors

    if not isinstance(vector_config, VectorParams):
        raise ValueError(
            "Expected an unnamed dense vector configuration"
        )

    if vector_config.size != vector_size:
        raise ValueError(
            "Qdrant vector size does not match configuration: "
            f"expected={vector_size}, "
            f"actual={vector_config.size}"
        )

    if vector_config.distance != Distance.COSINE:
        raise ValueError(
            "Qdrant collection must use cosine distance"
        )

    ensure_knowledge_payload_indexes(
        client,
        collection_name=collection_name,
    )

    if vector_config.distance != Distance.COSINE:
        raise ValueError(
            "Qdrant collection must use cosine distance"
        )

    ensure_knowledge_payload_indexes(
        client,
        collection_name=collection_name,
    )

def ensure_knowledge_payload_indexes(
    client: QdrantClient,
    *,
    collection_name: str,
) -> None:
    """Create indexes required by knowledge retrieval filters."""

    if not client.collection_exists(
        collection_name
    ):
        raise RuntimeError(
            "Configured Qdrant collection does not exist"
        )

    for field_name in (
        "access_scope",
        "source_id",
        "source_version",
    ):
        ensure_payload_index(
            client,
            collection_name=collection_name,
            field_name=field_name,
            field_schema=PayloadSchemaType.KEYWORD,
        )
