from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts.db_models import ContractDocumentRecord


class ContractDocumentRepository:
    """Read and write contract document records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(
        self,
        *,
        contract_id: UUID,
        access_scope: str,
    ) -> ContractDocumentRecord | None:
        """Find one contract without crossing its access scope."""

        statement = select(
            ContractDocumentRecord
        ).where(
            ContractDocumentRecord.contract_id
            == contract_id,
            ContractDocumentRecord.access_scope
            == access_scope,
        )

        return self._session.scalar(statement)

    def get_by_checksum(
        self,
        *,
        checksum_sha256: str,
        access_scope: str,
    ) -> ContractDocumentRecord | None:
        """Find an existing upload in the same access scope."""

        statement = select(
            ContractDocumentRecord
        ).where(
            ContractDocumentRecord.checksum_sha256
            == checksum_sha256,
            ContractDocumentRecord.access_scope
            == access_scope,
        )

        return self._session.scalar(statement)

    def add(
        self,
        record: ContractDocumentRecord,
    ) -> ContractDocumentRecord:
        """Stage a new document and assign database defaults."""

        self._session.add(record)
        self._session.flush()

        return record
