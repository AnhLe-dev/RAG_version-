from enum import Enum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)


NonEmptyText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]

CaseId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^ucp600_[0-9]{3}$",
    ),
]


class EvaluationCategory(str, Enum):
    """Classify the reasoning shape required by one case."""

    SINGLE_CLAUSE = "single_clause"
    CONDITIONAL = "conditional"
    MULTI_CLAUSE = "multi_clause"


class ReviewStatus(str, Enum):
    """Track whether a human has approved the reference label."""

    DRAFT = "draft"
    REVIEWED = "reviewed"


class EvaluationCase(BaseModel):
    """Represent one immutable UCP 600 evaluation case."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    case_id: CaseId
    user_input: NonEmptyText
    reference: NonEmptyText

    reference_contexts: tuple[
        NonEmptyText,
        ...,
    ] = Field(min_length=1)

    reference_evidence_ids: tuple[
        NonEmptyText,
        ...,
    ] = Field(min_length=1)

    category: EvaluationCategory
    review_status: ReviewStatus

    @field_validator(
        "reference_contexts",
        "reference_evidence_ids",
    )
    @classmethod
    def reject_duplicate_values(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Reject duplicated contexts or evidence identifiers."""

        if len(values) != len(set(values)):
            raise ValueError(
                "Values must be unique"
            )

        return values