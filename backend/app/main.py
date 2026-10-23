import logging
#logging: lấy logger cho module app.main.
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
#asynccontextmanager: quản lý vòng đời khởi động và dừng ứng dụng.

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging

from app.api.routes.rag import router as rag_router
from app.rag.service import create_rag_service

settings = get_settings()
configure_logging(settings.log_level)

logger = logging.getLogger(__name__)
@asynccontextmanager
async def lifespan(
    application: FastAPI,
) -> AsyncIterator[None]:
    """Create and close application resources."""

    logger.info("Application startup")

    rag_service = create_rag_service(
        settings
    )

    application.state.rag_service = (
        rag_service
    )

    try:
        yield
    finally:
        rag_service.close()
        logger.info("Application shutdown")

app = FastAPI(
    title="Legal Compliance RAG API",
    lifespan=lifespan,
)

app.include_router(rag_router)

@app.get("/")
def root() -> dict[str, str]:
    return {"message": "RAG API is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}

