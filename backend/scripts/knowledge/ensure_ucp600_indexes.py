from app.core.config import get_settings
from app.rag.vector_store.qdrant_store import (
    create_qdrant_client,
    ensure_knowledge_payload_indexes,
)


_REQUIRED_INDEXES = (
    "access_scope",
    "source_id",
    "source_version",
)


def main() -> None:
    """Create and verify UCP 600 retrieval indexes."""

    settings = get_settings()
    client = create_qdrant_client(settings)

    try:
        ensure_knowledge_payload_indexes(
            client,
            collection_name=(
                settings.qdrant_collection_name
            ),
        )

        collection = client.get_collection(
            settings.qdrant_collection_name
        )

        print("Knowledge payload indexes passed")

        for field_name in _REQUIRED_INDEXES:
            index = collection.payload_schema.get(
                field_name
            )

            if index is None:
                raise RuntimeError(
                    f"Payload index was not created: "
                    f"{field_name}"
                )

            print(
                f"{field_name}="
                f"{index.data_type.value}"
            )
    finally:
        client.close()


if __name__ == "__main__":
    main()