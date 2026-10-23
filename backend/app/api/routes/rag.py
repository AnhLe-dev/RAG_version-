from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    status,
)

from app.api.dependencies import (
    get_rag_service,
)
from app.api.schemas.rag import (
    RagQuestionRequest,
)
from app.rag.models import RagAnswer
from app.rag.service import RagService


router = APIRouter(
    prefix="/api/v1/rag",
    tags=["rag"],
)


@router.post(
    "/ask",
    response_model=RagAnswer,
    status_code=status.HTTP_200_OK,
)
def ask_rag(
    request_body: RagQuestionRequest,
    rag_service: Annotated[
        RagService,
        Depends(get_rag_service),
    ],
) -> RagAnswer:
    """Answer one public UCP 600 question."""

    return rag_service.ask(
        question=request_body.question,
        access_scope="public",
    )