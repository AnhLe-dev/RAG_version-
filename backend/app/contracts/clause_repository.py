from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.contracts.db_models import (
    ContractClauseRecord,
    ContractClauseSpanRecord,
    ContractDocumentRecord,
    ContractTextBlockRecord,
)
from app.contracts.models import (
    ContractClause,
    ContractSourceSpan,
)


class ContractClauseRepository:
    """Load contract clauses with their source locations."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def _source_options(self):
        """Eager-load spans, blocks, and page dimensions."""

        return selectinload(
            ContractClauseRecord.spans
        ).selectinload(
            ContractClauseSpanRecord.block
        ).selectinload(
            ContractTextBlockRecord.page
        )

    def get_by_label(
        self,
        *,
        contract_id: UUID,
        access_scope: str,
        label: str,
    ) -> ContractClauseRecord | None:
        """Find a clause without crossing access boundaries."""

        statement = (
            select(ContractClauseRecord)
            .join(ContractDocumentRecord)
            .options(self._source_options())
            .where(
                ContractClauseRecord.contract_id
                == contract_id,
                ContractDocumentRecord.access_scope
                == access_scope,
                ContractClauseRecord.label
                == label,
            )
        )

        return self._session.scalar(statement)

    def get_by_id(
        self,
        *,
        contract_id: UUID,
        access_scope: str,
        clause_id: UUID,
    ) -> ContractClauseRecord | None:
        """Find a clause by its ID within one contract."""

        statement = (
            select(ContractClauseRecord)
            .join(ContractDocumentRecord)
            .options(self._source_options())
            .where(
                ContractClauseRecord.contract_id
                == contract_id,
                ContractDocumentRecord.access_scope
                == access_scope,
                ContractClauseRecord.clause_id
                == clause_id,
            )
        )

        return self._session.scalar(statement)

    def to_domain(
        self,
        record: ContractClauseRecord,
    ) -> ContractClause:
        """Convert a database clause into its domain model."""

        source_spans = tuple(
            ContractSourceSpan(
                page_number=span.block.page_number,
                block_index=span.block.block_index,
                bbox=(
                    span.block.x0,
                    span.block.y0,
                    span.block.x1,
                    span.block.y1,
                ),
                page_width=span.block.page.width,
                page_height=span.block.page.height,
                char_start=span.char_start,
                char_end=span.char_end,
            )
            for span in record.spans
        )

        return ContractClause(
            clause_id=record.clause_id,
            contract_id=record.contract_id,
            parent_clause_id=record.parent_clause_id,
            label=record.label,
            title=record.title,
            raw_text=record.raw_text,
            kind=record.kind,
            order_index=record.order_index,
            page_start=record.page_start,
            page_end=record.page_end,
            source_spans=source_spans,
        )
