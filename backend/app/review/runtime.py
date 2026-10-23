from types import TracebackType

from langchain_core.tools import StructuredTool
from sqlalchemy import Engine

from app.core.config import Settings
from app.db.session import (
    create_database_engine,
    create_session_factory,
)
from app.knowledge import (
    KnowledgeRetrievalService,
    create_knowledge_retrieval_service,
    create_ucp600_reference_service,
)
from app.review.tools import create_review_tools


class ReviewToolRuntime:
    """Own review tools and their external resources."""

    def __init__(
        self,
        *,
        tools: tuple[StructuredTool, ...],
        engine: Engine,
        knowledge_service: KnowledgeRetrievalService,
    ) -> None:
        self._tools = tools
        self._engine = engine
        self._knowledge_service = (
            knowledge_service
        )
        self._closed = False

    @property
    def tools(
        self,
    ) -> tuple[StructuredTool, ...]:
        """Return the configured review tools."""

        if self._closed:
            raise RuntimeError(
                "Review tool runtime is closed"
            )

        return self._tools

    def close(self) -> None:
        """Close Qdrant and database resources once."""

        if self._closed:
            return

        self._closed = True

        try:
            self._knowledge_service.close()
        finally:
            self._engine.dispose()

    def __enter__(
        self,
    ) -> "ReviewToolRuntime":
        """Enter a managed runtime context."""

        if self._closed:
            raise RuntimeError(
                "Review tool runtime is closed"
            )

        return self

    def __exit__(
        self,
        exception_type: type[
            BaseException
        ] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Always release owned resources."""

        self.close()


def create_review_tool_runtime(
    *,
    settings: Settings,
    access_scope: str,
) -> ReviewToolRuntime:
    """Create review tools with production dependencies."""

    engine = create_database_engine(settings)
    knowledge_service = None

    try:
        session_factory = create_session_factory(
            engine
        )

        knowledge_service = (
            create_knowledge_retrieval_service(
                settings
            )
        )

        reference_service = (
            create_ucp600_reference_service(
                settings
            )
        )

        tools = create_review_tools(
            session_factory=session_factory,
            knowledge_service=knowledge_service,
            reference_service=reference_service,
            access_scope=access_scope,
        )

        return ReviewToolRuntime(
            tools=tools,
            engine=engine,
            knowledge_service=knowledge_service,
        )
    except Exception:
        if knowledge_service is not None:
            knowledge_service.close()

        engine.dispose()

        raise