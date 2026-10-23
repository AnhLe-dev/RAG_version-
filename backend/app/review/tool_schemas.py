from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)

from app.contracts.models import ContractClause
from app.rag.models import (
    ReferenceClause,
    RetrievedChunk,
)


class GetContractClausesInput(BaseModel):
    """Input for retrieving contract clauses."""

    contract_id: UUID

    labels: tuple[
        str,
        ...,
    ] = Field(
        min_length=1,
        max_length=20,
    )

    @field_validator(
        "labels",
        mode="before",
    )
    @classmethod
    def normalize_labels(
        cls,
        value: object,
    ) -> object:
        """Normalize and deduplicate labels."""

        if not isinstance(
            value,
            (list, tuple),
        ):
            raise ValueError(
                "Labels must be an array"
            )

        normalized_labels: list[str] = []

        for label in value:
            if not isinstance(label, str):
                raise ValueError(
                    "Every clause label must be a string"
                )

            normalized_label = (
                label.strip().upper()
            )

            if not normalized_label:
                raise ValueError(
                    "Clause label must not be blank"
                )

            if (
                normalized_label
                not in normalized_labels
            ):
                normalized_labels.append(
                    normalized_label
                )

        return tuple(normalized_labels)


class SearchKnowledgeInput(BaseModel):
    """Input for finding knowledge for one contract clause."""

    contract_id: UUID
    clause_label: str = Field(
        min_length=1,
        max_length=64,
    )
    question: str = Field(
        min_length=1,
        max_length=2000,
    )

    @field_validator("clause_label")
    @classmethod
    def normalize_clause_label(
        cls,
        value: str,
    ) -> str:
        """Normalize one contract clause label."""

        normalized_value = value.strip().upper()

        if not normalized_value:
            raise ValueError(
                "Clause label must not be blank"
            )

        return normalized_value

    @field_validator("question")
    @classmethod
    def normalize_question(
        cls,
        value: str,
    ) -> str:
        """Remove surrounding question whitespace."""

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(
                "Question must not be blank"
            )

        return normalized_value


class GetReferenceClauseInput(BaseModel):
    """Input for reading one complete UCP 600 article."""

    article_number: int = Field(
        ge=1,
        le=39,
    )


class GetContractClausesOutput(BaseModel):
    """Output containing trusted contract clauses."""

    contract_id: UUID

    clauses: tuple[
        ContractClause,
        ...,
    ] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_contract(
        self,
    ) -> "GetContractClausesOutput":
        """Ensure all clauses belong to the requested contract."""

        if any(
            clause.contract_id != self.contract_id
            for clause in self.clauses
        ):
            raise ValueError(
                "Tool output contains a clause "
                "from another contract"
            )

        return self


class SearchKnowledgeOutput(BaseModel):
    """Output containing retrieved knowledge evidence."""

    contract_id: UUID
    clause_id: UUID
    clause_label: str = Field(min_length=1)

    evidence: tuple[
        RetrievedChunk,
        ...,
    ] = ()


class GetReferenceClauseOutput(BaseModel):
    """Output containing one complete reference clause."""

    reference_clause: ReferenceClause