from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class RagQuestionRequest(BaseModel):
    """Represent one RAG question received by the API."""

    question: str = Field(
        min_length=1,
        max_length=2000,
    )

    @field_validator("question")
    @classmethod
    def normalize_question(
        cls,
        value: str,
    ) -> str:
        """Remove surrounding whitespace and reject blank input."""

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(
                "Question must not be empty"
            )

        return normalized_value