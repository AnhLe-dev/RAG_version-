from fastapi import Request

from app.rag.service import RagService


def get_rag_service(
    request: Request,
) -> RagService:
    """Return the application RAG service."""

    service = getattr(
        request.app.state,
        "rag_service",
        None,
    )

    if not isinstance(service, RagService):
        raise RuntimeError(
            "RAG service is not initialized"
        )

    return service