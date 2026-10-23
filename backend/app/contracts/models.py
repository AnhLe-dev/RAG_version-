from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)


class ContractStatus(StrEnum):
    """Represent the contract ingestion lifecycle."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    PARTIAL = "partial"
    FAILED = "failed"


class PageProcessingStatus(StrEnum):
    """Describe how one PDF page was handled."""

    TEXT = "text"
    IGNORED_COVER = "ignored_cover"
    IGNORED_OUT_OF_SCOPE = "ignored_out_of_scope"
    OCR_REQUIRED = "ocr_required"


class ClauseKind(StrEnum):
    """Distinguish SWIFT fields from their numbered items."""

    SWIFT_FIELD = "swift_field"
    SWIFT_ITEM = "swift_item"


class ContractSourceSpan(BaseModel):
    """Map contract text back to one positioned PDF block."""

    page_number: int = Field(ge=1)
    block_index: int = Field(ge=0)

    bbox: tuple[
        float,
        float,
        float,
        float,
    ]

    page_width: float = Field(gt=0)
    page_height: float = Field(gt=0)

    char_start: int | None = Field(
        default=None,
        ge=0,
    )
    char_end: int | None = Field(
        default=None,
        ge=1,
    )

    @model_validator(mode="after")
    def validate_span(self) -> "ContractSourceSpan":
        """Validate coordinates and optional character offsets."""

        x0, y0, x1, y1 = self.bbox

        if x1 <= x0 or y1 <= y0:
            raise ValueError(
                "Source span bounding box must have "
                "positive width and height"
            )

        has_start = self.char_start is not None
        has_end = self.char_end is not None

        if has_start != has_end:
            raise ValueError(
                "CHAR_START and CHAR_END must be "
                "provided together"
            )

        if (
            self.char_start is not None
            and self.char_end is not None
            and self.char_end <= self.char_start
        ):
            raise ValueError(
                "CHAR_END must be greater than CHAR_START"
            )

        return self


class ContractDocument(BaseModel):
    """Represent one stored contract or letter of credit."""

    contract_id: UUID
    filename: str = Field(min_length=1)
    version: int = Field(default=1, ge=1)

    checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )

    object_key: str = Field(min_length=1)

    document_type: Literal[
        "swift_mt700"
    ] = "swift_mt700"

    status: ContractStatus
    access_scope: str = Field(min_length=1)
    page_count: int = Field(ge=1)

    processed_pages: tuple[int, ...] = ()
    ignored_pages: tuple[int, ...] = ()
    ocr_required_pages: tuple[int, ...] = ()

    error_code: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_processing_state(
        self,
    ) -> "ContractDocument":
        """Validate page coverage and terminal status."""

        page_groups = (
            self.processed_pages,
            self.ignored_pages,
            self.ocr_required_pages,
        )

        for pages in page_groups:
            if len(pages) != len(set(pages)):
                raise ValueError(
                    "Page lists must not contain duplicates"
                )

            if any(
                page < 1 or page > self.page_count
                for page in pages
            ):
                raise ValueError(
                    "Page number is outside the document"
                )

        processed = set(self.processed_pages)
        ignored = set(self.ignored_pages)
        ocr_required = set(
            self.ocr_required_pages
        )

        if (
            processed & ignored
            or processed & ocr_required
            or ignored & ocr_required
        ):
            raise ValueError(
                "A page cannot have multiple processing states"
            )

        if self.status in {
            ContractStatus.READY,
            ContractStatus.PARTIAL,
        }:
            covered_pages = (
                processed
                | ignored
                | ocr_required
            )
            expected_pages = set(
                range(1, self.page_count + 1)
            )

            if covered_pages != expected_pages:
                raise ValueError(
                    "Terminal document status requires "
                    "classification of every page"
                )

        if (
            self.status == ContractStatus.READY
            and ocr_required
        ):
            raise ValueError(
                "READY document cannot contain OCR-required pages"
            )

        if (
            self.status == ContractStatus.PARTIAL
            and not ocr_required
        ):
            raise ValueError(
                "PARTIAL document must contain "
                "OCR-required pages"
            )

        if (
            self.status == ContractStatus.FAILED
            and not self.error_code
        ):
            raise ValueError(
                "FAILED document requires an error code"
            )

        return self


class ContractClause(BaseModel):
    """Represent one SWIFT field or numbered sub-item."""

    clause_id: UUID
    contract_id: UUID
    parent_clause_id: UUID | None = None

    label: str = Field(min_length=1)
    title: str = Field(min_length=1)
    raw_text: str = Field(min_length=1)

    kind: ClauseKind
    order_index: int = Field(ge=0)

    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)

    source_spans: tuple[
        ContractSourceSpan,
        ...,
    ] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_page_range(
        self,
    ) -> "ContractClause":
        """Ensure page range matches the source spans."""

        if self.page_end < self.page_start:
            raise ValueError(
                "PAGE_END must be greater than or "
                "equal to PAGE_START"
            )

        span_pages = {
            span.page_number
            for span in self.source_spans
        }

        if self.page_start != min(span_pages):
            raise ValueError(
                "PAGE_START must match source spans"
            )

        if self.page_end != max(span_pages):
            raise ValueError(
                "PAGE_END must match source spans"
            )

        if (
            self.kind == ClauseKind.SWIFT_FIELD
            and self.parent_clause_id is not None
        ):
            raise ValueError(
                "SWIFT_FIELD cannot have a parent clause"
            )

        if (
            self.kind == ClauseKind.SWIFT_ITEM
            and self.parent_clause_id is None
        ):
            raise ValueError(
                "SWIFT_ITEM requires a parent clause"
            )

        return self
