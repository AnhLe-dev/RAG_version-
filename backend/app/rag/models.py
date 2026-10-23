from __future__ import annotations
from pydantic import BaseModel, Field, model_validator


class SourceDocument(BaseModel):
    """Describe an original document entering the ingestion pipeline."""

    source_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    #tránh các tệp giống nhau đưa vào hệ thống
    access_scope: str = Field(min_length=1)

class DocumentChunk(BaseModel):
    """Represent a traceable text chunk produced from a source document."""

    chunk_id: str = Field(min_length=1)

    source_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    source_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )

    text: str = Field(min_length=1)
    article_number: int = Field(ge=1, le=39)
    structure_path: tuple[str, ...] = Field(min_length=1)

    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    source_spans: tuple[SourceSpan, ...] = Field(
        min_length=1
    )

    parent_chunk_id: str | None = None
    access_scope: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_source_span(self) -> "DocumentChunk":
        """Ensure the chunk page range matches its source spans."""

        span_pages = [
            span.page_number
            for span in self.source_spans
        ]

        if self.page_start != min(span_pages):
            raise ValueError(
                "PAGE_START must match the first source span page"
            )

        if self.page_end != max(span_pages):
            raise ValueError(
                "PAGE_END must match the last source span page"
            )

        return self

class PageTextBlock(BaseModel):
    """Represent a positioned text block extracted from a PDF page."""

    block_index: int = Field(ge=0)
    text: str = Field(min_length=1)
    bbox: tuple[float, float, float, float]

    @model_validator(mode="after")
    def validate_bounding_box(self) -> "PageTextBlock":
        """Ensure the bounding box has a positive width and height."""

        x0, y0, x1, y1 = self.bbox

        if x1 <= x0 or y1 <= y0:
            raise ValueError(
                "Bounding box must have a positive width and height"
            )

        return self

class ExtractedPage(BaseModel):
    """Represent text blocks extracted from one PDF page."""

    page_number: int = Field(ge=1)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    blocks: tuple[PageTextBlock, ...]

class LocatedTextBlock(PageTextBlock):
    """Represent a text block with its original page number."""

    page_number: int = Field(ge=1)

class LegalArticle(BaseModel):
    """Represent one UCP 600 article and its traceable content blocks."""

    article_number: int = Field(ge=1, le=39)
    title: str = Field(min_length=1)
    heading: LocatedTextBlock
    content_blocks: tuple[LocatedTextBlock, ...] = Field(
        min_length=1
    )

    @property
    def page_start(self) -> int:
        """Return the first source page of the article."""

        return min(
            self.heading.page_number,
            *(block.page_number for block in self.content_blocks),
        )

    @property
    def page_end(self) -> int:
        """Return the last source page of the article."""

        return max(
            self.heading.page_number,
            *(block.page_number for block in self.content_blocks),
        )

    @property
    def text(self) -> str:
        """Return article content joined in reading order."""

        return "\n".join(
            block.text
            for block in self.content_blocks
        )

class LegalParagraph(BaseModel):
    """Represent one top-level paragraph of a UCP 600 article."""

    article_number: int = Field(ge=1, le=39)
    label: str | None = Field(
        default=None,
        pattern=r"^[a-z]$",
    )
    content_blocks: tuple[LocatedTextBlock, ...] = Field(
        min_length=1
    )

    @property
    def page_start(self) -> int:
        """Return the first source page of the paragraph."""

        return min(
            block.page_number
            for block in self.content_blocks
        )

    @property
    def page_end(self) -> int:
        """Return the last source page of the paragraph."""

        return max(
            block.page_number
            for block in self.content_blocks
        )

    @property
    def text(self) -> str:
        """Return paragraph content in reading order."""

        return "\n".join(
            block.text
            for block in self.content_blocks
        )
    
class LegalItem(BaseModel):
    """Represent one Roman-numbered item inside a legal paragraph."""

    article_number: int = Field(ge=1, le=39)
    paragraph_label: str | None = Field(
        default=None,
        pattern=r"^[a-z]$",
    )
    label: str | None = Field(
        default=None,
        pattern=r"^(i|ii|iii|iv|v|vi|vii|viii|ix|x)$",
    )
    content_blocks: tuple[LocatedTextBlock, ...] = Field(
        min_length=1
    )

    @property
    def page_start(self) -> int:
        """Return the first source page of the item."""

        return min(
            block.page_number
            for block in self.content_blocks
        )

    @property
    def page_end(self) -> int:
        """Return the last source page of the item."""

        return max(
            block.page_number
            for block in self.content_blocks
        )

    @property
    def text(self) -> str:
        """Return item content in reading order."""

        return "\n".join(
            block.text
            for block in self.content_blocks
        )

class SourceSpan(BaseModel):
    """xác định 1 block nằm ở trang nào, block nào, toạ độ nào"""

    page_number: int = Field(ge=1)
    block_index: int = Field(ge=0)
    bbox: tuple[float, float, float, float]

DocumentChunk.model_rebuild()   

class RetrievedChunk(BaseModel):
    """Represent one traceable chunk returned by retrieval."""

    chunk_id: str = Field(min_length=1)

    source_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    source_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )

    text: str = Field(min_length=1)
    article_number: int = Field(ge=1, le=39)
    structure_path: tuple[str, ...] = Field(
        min_length=1
    )

    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    source_spans: tuple[
        SourceSpan,
        ...,
    ] = Field(min_length=1)

    parent_chunk_id: str | None = None
    access_scope: str = Field(min_length=1)
    score: float

    @model_validator(mode="after")
    def validate_source_mapping(
        self,
    ) -> "RetrievedChunk":
        """Ensure the page range matches the source spans."""

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

        return self


class ReferenceClause(BaseModel):
    """Represent one complete clause from a knowledge source."""

    source_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    source_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )

    article_number: int = Field(ge=1, le=39)
    title: str = Field(min_length=1)
    raw_text: str = Field(min_length=1)

    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    source_spans: tuple[
        SourceSpan,
        ...,
    ] = Field(min_length=1)

    access_scope: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_source_mapping(
        self,
    ) -> "ReferenceClause":
        """Ensure the page range matches the source spans."""

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

        return self

class RagCitation(BaseModel):
    """Represent one source cited by a RAG answer."""

    citation_id: str = Field(
        pattern=r"^S[1-9]\d*$"
    )

    chunk_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1)

    article_number: int = Field(ge=1, le=39)
    structure_path: tuple[str, ...] = Field(
        min_length=1
    )

    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)

    text: str = Field(min_length=1)
    score: float

class RagAnswer(BaseModel):
    """Represent a grounded answer and its cited sources."""

    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)

    citations: tuple[RagCitation, ...] = Field(
        min_length=1
    )

    retrieved_count: int = Field(ge=1)

