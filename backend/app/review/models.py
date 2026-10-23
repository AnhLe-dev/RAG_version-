from enum import StrEnum
from uuid import UUID
from app.contracts.models import ContractClause
from app.rag.models import RetrievedChunk
from pydantic import (
    BaseModel,
    Field,
    model_validator,
)


class ReviewFindingStatus(StrEnum):
    """Represent the result of reviewing one contract clause."""

    NON_COMPLIANT = "non_compliant"
    NO_ISSUE_FOUND = "no_issue_found"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ReviewFinding(BaseModel):
    """Represent one structured contract review finding."""

    contract_id: UUID
    clause_id: UUID
    clause_label: str = Field(min_length=1)
    contract_quote: str = Field(min_length=1)

    status: ReviewFindingStatus
    reason: str = Field(min_length=1)

    evidence_chunk_ids: tuple[
        str,
        ...,
    ] = ()

    @model_validator(mode="after")
    def validate_finding(
        self,
    ) -> "ReviewFinding":
        """Validate text and evidence requirements."""

        if not self.clause_label.strip():
            raise ValueError(
                "Clause label must not be blank"
            )

        if not self.contract_quote.strip():
            raise ValueError(
                "Contract quote must not be blank"
            )

        if not self.reason.strip():
            raise ValueError(
                "Finding reason must not be blank"
            )

        if (
            len(self.evidence_chunk_ids)
            != len(set(self.evidence_chunk_ids))
        ):
            raise ValueError(
                "Evidence chunk IDs must be unique"
            )

        if any(
            not chunk_id.strip()
            for chunk_id in self.evidence_chunk_ids
        ):
            raise ValueError(
                "Evidence chunk ID must not be blank"
            )

        if (
            self.status
            in {
                ReviewFindingStatus.NON_COMPLIANT,
                ReviewFindingStatus.NO_ISSUE_FOUND,
            }
            and not self.evidence_chunk_ids
        ):
            raise ValueError(
                "A conclusive finding requires evidence"
            )

        return self


class ReviewResult(BaseModel):
    """Represent the complete structured review response."""

    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)

    contract_id: UUID

    checked_clause_ids: tuple[
        UUID,
        ...,
    ] = Field(min_length=1)

    knowledge_source_id: str = Field(min_length=1)
    knowledge_source_version: str = Field(
        min_length=1
    )

    findings: tuple[
        ReviewFinding,
        ...,
    ] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_result(
        self,
    ) -> "ReviewResult":
        """Validate review scope and finding ownership."""

        if not self.question.strip():
            raise ValueError(
                "Review question must not be blank"
            )

        if not self.answer.strip():
            raise ValueError(
                "Review answer must not be blank"
            )

        if not self.knowledge_source_id.strip():
            raise ValueError(
                "Knowledge source ID must not be blank"
            )

        if not self.knowledge_source_version.strip():
            raise ValueError(
                "Knowledge source version must not be blank"
            )

        if (
            len(self.checked_clause_ids)
            != len(set(self.checked_clause_ids))
        ):
            raise ValueError(
                "Checked clause IDs must be unique"
            )

        checked_clause_ids = set(
            self.checked_clause_ids
        )

        for finding in self.findings:
            if finding.contract_id != self.contract_id:
                raise ValueError(
                    "Finding belongs to another contract"
                )

            if finding.clause_id not in checked_clause_ids:
                raise ValueError(
                    "Finding clause is outside "
                    "the checked scope"
                )

        return self

class ReviewValidationContext(BaseModel):
    """Contain trusted data available during review validation."""

    contract_id: UUID

    contract_clauses: tuple[
        ContractClause,
        ...,
    ] = Field(min_length=1)

    knowledge_evidence: tuple[
        RetrievedChunk,
        ...,
    ] = ()

    @model_validator(mode="after")
    def validate_context(
        self,
    ) -> "ReviewValidationContext":
        """Validate trusted contract and evidence collections."""

        clause_ids = [
            clause.clause_id
            for clause in self.contract_clauses
        ]

        if len(clause_ids) != len(set(clause_ids)):
            raise ValueError(
                "Validation context contains "
                "duplicate contract clauses"
            )

        for clause in self.contract_clauses:
            if clause.contract_id != self.contract_id:
                raise ValueError(
                    "Validation context contains a clause "
                    "from another contract"
                )

        evidence_chunk_ids = [
            evidence.chunk_id
            for evidence in self.knowledge_evidence
        ]

        if (
            len(evidence_chunk_ids)
            != len(set(evidence_chunk_ids))
        ):
            raise ValueError(
                "Validation context contains "
                "duplicate knowledge evidence"
            )

        return self