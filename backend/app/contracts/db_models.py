from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    UUID as PostgresUUID,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.contracts.models import (
    ClauseKind,
    ContractStatus,
    PageProcessingStatus,
)
from app.db import Base


def enum_values(
    enum_class: type,
) -> list[str]:
    """Persist enum values instead of Python member names."""

    return [
        member.value
        for member in enum_class
    ]


class ContractDocumentRecord(Base):
    """Persist metadata and processing state for one PDF."""

    __tablename__ = "contract_documents"
    __table_args__ = (
        UniqueConstraint(
            "access_scope",
            "checksum_sha256",
            name="uq_contract_scope_checksum",
        ),
    )

    contract_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    filename: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    object_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        unique=True,
    )

    document_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="swift_mt700",
    )
    status: Mapped[ContractStatus] = mapped_column(
        SqlEnum(
            ContractStatus,
            name="contract_status",
            values_callable=enum_values,
        ),
        nullable=False,
        index=True,
    )
    access_scope: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    page_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    processed_pages: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        default=list,
    )
    ignored_pages: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        default=list,
    )
    ocr_required_pages: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        default=list,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    pages: Mapped[
        list[ContractPageRecord]
    ] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ContractPageRecord.page_number",
    )

    clauses: Mapped[
        list[ContractClauseRecord]
    ] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ContractClauseRecord.order_index",
    )


class ContractPageRecord(Base):
    """Persist dimensions and processing state of one page."""

    __tablename__ = "contract_pages"

    contract_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey(
            "contract_documents.contract_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    page_number: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    width: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    height: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    processing_status: Mapped[
        PageProcessingStatus
    ] = mapped_column(
        SqlEnum(
            PageProcessingStatus,
            name="page_processing_status",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    text_block_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    document: Mapped[
        ContractDocumentRecord
    ] = relationship(
        back_populates="pages",
    )

    blocks: Mapped[
        list[ContractTextBlockRecord]
    ] = relationship(
        back_populates="page",
        cascade="all, delete-orphan",
        order_by="ContractTextBlockRecord.sort_index",
    )


class ContractTextBlockRecord(Base):
    """Persist one positioned text block from the PDF."""

    __tablename__ = "contract_text_blocks"
    __table_args__ = (
        ForeignKeyConstraint(
            [
                "contract_id",
                "page_number",
            ],
            [
                "contract_pages.contract_id",
                "contract_pages.page_number",
            ],
            ondelete="CASCADE",
            name="fk_contract_block_page",
        ),
        UniqueConstraint(
            "contract_id",
            "page_number",
            "block_index",
            name="uq_contract_page_block",
        ),
    )

    block_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    contract_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    block_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    sort_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    raw_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    x0: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    y0: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    x1: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    y1: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    is_content: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    page: Mapped[ContractPageRecord] = relationship(
        back_populates="blocks",
    )

    clause_spans: Mapped[
        list[ContractClauseSpanRecord]
    ] = relationship(
        back_populates="block",
    )


class ContractClauseRecord(Base):
    """Persist one MT700 field or numbered child item."""

    __tablename__ = "contract_clauses"
    __table_args__ = (
        UniqueConstraint(
            "contract_id",
            "label",
            name="uq_contract_clause_label",
        ),
    )

    clause_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
    )
    contract_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey(
            "contract_documents.contract_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    parent_clause_id: Mapped[
        UUID | None
    ] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey(
            "contract_clauses.clause_id",
            ondelete="CASCADE",
        ),
        nullable=True,
    )

    label: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    raw_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    kind: Mapped[ClauseKind] = mapped_column(
        SqlEnum(
            ClauseKind,
            name="clause_kind",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    page_start: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    page_end: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    document: Mapped[
        ContractDocumentRecord
    ] = relationship(
        back_populates="clauses",
    )

    parent: Mapped[
        ContractClauseRecord | None
    ] = relationship(
        remote_side="ContractClauseRecord.clause_id",
        back_populates="children",
    )

    children: Mapped[
        list[ContractClauseRecord]
    ] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        single_parent=True,
        order_by="ContractClauseRecord.order_index",
    )

    spans: Mapped[
        list[ContractClauseSpanRecord]
    ] = relationship(
        back_populates="clause",
        cascade="all, delete-orphan",
        order_by="ContractClauseSpanRecord.span_order",
    )


class ContractClauseSpanRecord(Base):
    """Link a clause to its ordered source blocks."""

    __tablename__ = "contract_clause_spans"

    clause_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey(
            "contract_clauses.clause_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    span_order: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    block_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey(
            "contract_text_blocks.block_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    char_start: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    char_end: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    clause: Mapped[
        ContractClauseRecord
    ] = relationship(
        back_populates="spans",
    )
    block: Mapped[
        ContractTextBlockRecord
    ] = relationship(
        back_populates="clause_spans",
    )