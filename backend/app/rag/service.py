from langchain_openai import (
    ChatOpenAI,
    OpenAIEmbeddings,
)
from qdrant_client import QdrantClient

from app.core.config import Settings
from app.rag.embedding.openai_embedder import (
    create_embedding_client,
)
from app.rag.generation.answer_generator import (
    create_answer_model,
    generate_answer,
)
from app.rag.generation.citation_validator import (
    validate_answer_citations,
)
from app.rag.generation.context_builder import (
    build_context,
)
from app.rag.generation.prompt_builder import (
    build_rag_prompt,
)
from app.rag.models import (
    RagAnswer,
    RagCitation,
    RetrievedChunk,
)
from app.rag.retrieval.dense_retriever import (
    search_dense,
)
from app.rag.vector_store.qdrant_store import (
    create_qdrant_client,
)


class RagService:
    """Coordinate the complete RAG question pipeline."""

    def __init__(
        self,
        *,
        settings: Settings,
        embedding_client: OpenAIEmbeddings,
        answer_model: ChatOpenAI,
        qdrant_client: QdrantClient,
    ) -> None:
        self._settings = settings
        self._embedding_client = embedding_client
        self._answer_model = answer_model
        self._qdrant_client = qdrant_client

    def ask(
        self,
        *,
        question: str,
        access_scope: str,
    ) -> RagAnswer:
        """Answer one question from retrieved UCP 600 context."""

        normalized_question = question.strip()
        normalized_scope = access_scope.strip()

        if not normalized_question:
            raise ValueError(
                "Question must not be empty"
            )

        if not normalized_scope:
            raise ValueError(
                "Access scope must not be empty"
            )

        query_vector = (
            self._embedding_client.embed_query(
                normalized_question
            )
        )

        results = search_dense(
            self._qdrant_client,
            collection_name=(
                self._settings.qdrant_collection_name
            ),
            query_vector=query_vector,
            access_scope=normalized_scope,
            source_id="ucp600",
            source_version="1",
            limit=self._settings.final_top_n,
            expected_dimensions=(
                self._settings.embedding_dimensions
            ),
        )

        context = build_context(results)

        prompt = build_rag_prompt(
            question=normalized_question,
            context=context,
        )

        answer = generate_answer(
            prompt=prompt,
            model=self._answer_model,
        )

        used_citations = validate_answer_citations(
            answer=answer,
            context=context,
        )

        citations = self._build_citations(
            used_citations=used_citations,
            results=results,
        )

        return RagAnswer(
            question=normalized_question,
            answer=answer,
            citations=citations,
            retrieved_count=len(results),
        )

    def close(self) -> None:
        """Close resources owned by this service."""

        self._qdrant_client.close()

    @staticmethod
    def _build_citations(
        *,
        used_citations: tuple[str, ...],
        results: tuple[RetrievedChunk, ...],
    ) -> tuple[RagCitation, ...]:
        """Map LLM citation labels back to retrieved chunks."""

        citations: list[RagCitation] = []

        for citation_id in used_citations:
            result_index = int(
                citation_id.removeprefix("S")
            ) - 1

            if not 0 <= result_index < len(results):
                raise ValueError(
                    "Citation does not map to a retrieval result: "
                    f"{citation_id}"
                )

            result = results[result_index]

            citations.append(
                RagCitation(
                    citation_id=citation_id,
                    chunk_id=result.chunk_id,
                    source_id=result.source_id,
                    source_version=(
                        result.source_version
                    ),
                    article_number=(
                        result.article_number
                    ),
                    structure_path=(
                        result.structure_path
                    ),
                    page_start=result.page_start,
                    page_end=result.page_end,
                    text=result.text,
                    score=result.score,
                )
            )

        return tuple(citations)


def create_rag_service(
    settings: Settings,
) -> RagService:
    """Create a RAG service with production dependencies."""

    return RagService(
        settings=settings,
        embedding_client=create_embedding_client(
            settings
        ),
        answer_model=create_answer_model(
            settings
        ),
        qdrant_client=create_qdrant_client(
            settings
        ),
    )