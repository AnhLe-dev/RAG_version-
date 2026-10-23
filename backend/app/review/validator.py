from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.review.models import (
    ReviewResult,
    ReviewValidationContext,
)


class ReviewValidationIssueCode(StrEnum):
    """Identify one deterministic review validation failure."""

    CONTRACT_MISMATCH = "contract_mismatch"
    CHECKED_CLAUSE_NOT_FOUND = (
        "checked_clause_not_found"
    )
    FINDING_CLAUSE_NOT_FOUND = (
        "finding_clause_not_found"
    )
    CLAUSE_LABEL_MISMATCH = (
        "clause_label_mismatch"
    )
    CONTRACT_QUOTE_MISMATCH = (
        "contract_quote_mismatch"
    )
    EVIDENCE_NOT_FOUND = "evidence_not_found"
    EVIDENCE_SOURCE_MISMATCH = (
        "evidence_source_mismatch"
    )
    EVIDENCE_VERSION_MISMATCH = (
        "evidence_version_mismatch"
    )


class ReviewValidationIssue(BaseModel):
    """Describe one validation issue with its location."""

    code: ReviewValidationIssueCode
    message: str = Field(min_length=1)

    finding_index: int | None = Field(
        default=None,
        ge=0,
    )
    clause_id: UUID | None = None
    evidence_chunk_id: str | None = None


class ReviewValidationError(ValueError):
    """Raised when a review result fails validation."""

    def __init__(
        self,
        issues: tuple[
            ReviewValidationIssue,
            ...,
        ],
    ) -> None:
        self.issues = issues

        issue_summary = "; ".join(
            (
                f"{issue.code.value}: "
                f"{issue.message}"
            )
            for issue in issues
        )

        super().__init__(
            f"Review validation failed: "
            f"{issue_summary}"
        )


def _normalize_source_text(
    value: str,
) -> str:
    """Normalize whitespace without changing source words."""

    return " ".join(value.split())


def validate_review_result(
    *,
    result: ReviewResult,
    context: ReviewValidationContext,
) -> ReviewResult:
    """Validate a review against trusted clauses and evidence."""

    issues: list[ReviewValidationIssue] = []

    if result.contract_id != context.contract_id:
        issues.append(
            ReviewValidationIssue(
                code=(
                    ReviewValidationIssueCode
                    .CONTRACT_MISMATCH
                ),
                message=(
                    "Review result belongs to "
                    "another contract"
                ),
            )
        )

    clauses_by_id = {
        clause.clause_id: clause
        for clause in context.contract_clauses
    }

    for clause_id in result.checked_clause_ids:
        if clause_id not in clauses_by_id:
            issues.append(
                ReviewValidationIssue(
                    code=(
                        ReviewValidationIssueCode
                        .CHECKED_CLAUSE_NOT_FOUND
                    ),
                    message=(
                        "Checked clause does not exist "
                        "in the validation context"
                    ),
                    clause_id=clause_id,
                )
            )

    evidence_by_id = {
        evidence.chunk_id: evidence
        for evidence in context.knowledge_evidence
    }

    for finding_index, finding in enumerate(
        result.findings
    ):
        clause = clauses_by_id.get(
            finding.clause_id
        )

        if clause is None:
            issues.append(
                ReviewValidationIssue(
                    code=(
                        ReviewValidationIssueCode
                        .FINDING_CLAUSE_NOT_FOUND
                    ),
                    message=(
                        "Finding clause does not exist "
                        "in the validation context"
                    ),
                    finding_index=finding_index,
                    clause_id=finding.clause_id,
                )
            )
        else:
            if (
                finding.clause_label.strip().upper()
                != clause.label.strip().upper()
            ):
                issues.append(
                    ReviewValidationIssue(
                        code=(
                            ReviewValidationIssueCode
                            .CLAUSE_LABEL_MISMATCH
                        ),
                        message=(
                            "Finding label does not match "
                            "the stored contract clause"
                        ),
                        finding_index=finding_index,
                        clause_id=finding.clause_id,
                    )
                )

            normalized_quote = _normalize_source_text(
                finding.contract_quote
            )
            normalized_clause_text = (
                _normalize_source_text(
                    clause.raw_text
                )
            )

            if (
                normalized_quote
                not in normalized_clause_text
            ):
                issues.append(
                    ReviewValidationIssue(
                        code=(
                            ReviewValidationIssueCode
                            .CONTRACT_QUOTE_MISMATCH
                        ),
                        message=(
                            "Contract quote was not found "
                            "in the stored clause text"
                        ),
                        finding_index=finding_index,
                        clause_id=finding.clause_id,
                    )
                )

        for evidence_chunk_id in (
            finding.evidence_chunk_ids
        ):
            evidence = evidence_by_id.get(
                evidence_chunk_id
            )

            if evidence is None:
                issues.append(
                    ReviewValidationIssue(
                        code=(
                            ReviewValidationIssueCode
                            .EVIDENCE_NOT_FOUND
                        ),
                        message=(
                            "Cited evidence was not returned "
                            "by knowledge retrieval"
                        ),
                        finding_index=finding_index,
                        clause_id=finding.clause_id,
                        evidence_chunk_id=(
                            evidence_chunk_id
                        ),
                    )
                )
                continue

            if (
                evidence.source_id
                != result.knowledge_source_id
            ):
                issues.append(
                    ReviewValidationIssue(
                        code=(
                            ReviewValidationIssueCode
                            .EVIDENCE_SOURCE_MISMATCH
                        ),
                        message=(
                            "Cited evidence belongs to "
                            "another knowledge source"
                        ),
                        finding_index=finding_index,
                        clause_id=finding.clause_id,
                        evidence_chunk_id=(
                            evidence_chunk_id
                        ),
                    )
                )

            if (
                evidence.source_version
                != result.knowledge_source_version
            ):
                issues.append(
                    ReviewValidationIssue(
                        code=(
                            ReviewValidationIssueCode
                            .EVIDENCE_VERSION_MISMATCH
                        ),
                        message=(
                            "Cited evidence belongs to "
                            "another source version"
                        ),
                        finding_index=finding_index,
                        clause_id=finding.clause_id,
                        evidence_chunk_id=(
                            evidence_chunk_id
                        ),
                    )
                )

    if issues:
        raise ReviewValidationError(
            tuple(issues)
        )

    return result