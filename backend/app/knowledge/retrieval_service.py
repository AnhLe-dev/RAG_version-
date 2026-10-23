from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient

from app.contracts.models import ContractClause
from app.core.config import Settings
from app.rag.embedding.openai_embedder import (
    create_embedding_client,
)
from app.rag.models import RetrievedChunk
from app.rag.retrieval.dense_retriever import (
    search_dense,
)
from app.rag.vector_store.qdrant_store import (
    create_qdrant_client,
)


def build_contract_knowledge_query(
    *,
    question: str,
    clause: ContractClause,
) -> str:
    """Build an embedding query from user intent and contract text."""

    normalized_question = question.strip()

    if not normalized_question:
        raise ValueError(
            "Question must not be empty"
        )

    return (
        "User question:\n"
        f"{normalized_question}\n\n"
        "Contract clause:\n"
        f"Label: {clause.label}\n"
        f"Title: {clause.title}\n"
        "Text:\n"
        f"{clause.raw_text.strip()}"
    )


class KnowledgeRetrievalService:
    """Find knowledge evidence for one contract clause."""

    def __init__(
        self,
        *,
        settings: Settings,
        embedding_client: OpenAIEmbeddings,
        qdrant_client: QdrantClient,
    ) -> None:
        self._settings = settings
        self._embedding_client = embedding_client
        self._qdrant_client = qdrant_client

    def search_contract_clause(
        self,
        *,
        question: str,
        clause: ContractClause,
        access_scope: str,
        source_id: str = "ucp600",
        source_version: str = "1",
    ) -> tuple[RetrievedChunk, ...]:
        """Retrieve evidence for one contract clause."""

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

        query_text = build_contract_knowledge_query(
            question=question,
            clause=clause,
        )

        query_vector = (
            self._embedding_client.embed_query(
                query_text
            )
        )

        return search_dense(
            self._qdrant_client,
            collection_name=(
                self._settings.qdrant_collection_name
            ),
            query_vector=query_vector,
            access_scope=normalized_scope,
            source_id=normalized_source_id,
            source_version=normalized_source_version,
            limit=self._settings.final_top_n,
            expected_dimensions=(
                self._settings.embedding_dimensions
            ),
        )

    def close(self) -> None:
        """Close the Qdrant client owned by this service."""

        self._qdrant_client.close()


def create_knowledge_retrieval_service(
    settings: Settings,
) -> KnowledgeRetrievalService:
    """Create knowledge retrieval with production dependencies."""

    return KnowledgeRetrievalService(
        settings=settings,
        embedding_client=create_embedding_client(
            settings
        ),
        qdrant_client=create_qdrant_client(
            settings
        ),
    )