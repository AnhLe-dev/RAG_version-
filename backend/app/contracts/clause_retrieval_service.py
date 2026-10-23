from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.clause_repository import (
    ContractClauseRepository,
)
from app.contracts.models import (
    ContractClause,
    ContractStatus,
)
from app.contracts.repository import (
    ContractDocumentRepository,
)


class ContractNotFoundError(LookupError):
    """Raised when a contract is unavailable in the access scope."""


class ContractNotReadyError(RuntimeError):
    """Raised when contract processing is incomplete."""


class ContractClauseNotFoundError(LookupError):
    """Raised when a requested clause does not exist."""


class ContractClauseRetrievalService:
    """Retrieve traceable clauses from one ready contract."""

    def __init__(
        self,
        *,
        session: Session,
    ) -> None:
        self._document_repository = (
            ContractDocumentRepository(session)
        )
        self._clause_repository = (
            ContractClauseRepository(session)
        )

    def _require_ready_contract(
        self,
        *,
        contract_id: UUID,
        access_scope: str,
    ) -> None:
        """Verify contract existence, scope, and processing state."""

        document = self._document_repository.get_by_id(
            contract_id=contract_id,
            access_scope=access_scope,
        )

        if document is None:
            raise ContractNotFoundError(
                "Contract document was not found"
            )

        if document.status != ContractStatus.READY:
            raise ContractNotReadyError(
                "Contract document is not ready"
            )

    def get_by_label(
        self,
        *,
        contract_id: UUID,
        access_scope: str,
        label: str,
    ) -> ContractClause:
        """Return one clause by its normalized MT700 label."""

        self._require_ready_contract(
            contract_id=contract_id,
            access_scope=access_scope,
        )

        normalized_label = label.strip().upper()

        if not normalized_label:
            raise ValueError(
                "Clause label must not be empty"
            )

        record = self._clause_repository.get_by_label(
            contract_id=contract_id,
            access_scope=access_scope,
            label=normalized_label,
        )

        if record is None:
            raise ContractClauseNotFoundError(
                "Contract clause was not found"
            )

        return self._clause_repository.to_domain(
            record
        )

    def get_by_id(
        self,
        *,
        contract_id: UUID,
        access_scope: str,
        clause_id: UUID,
    ) -> ContractClause:
        """Return one clause by its UUID."""

        self._require_ready_contract(
            contract_id=contract_id,
            access_scope=access_scope,
        )

        record = self._clause_repository.get_by_id(
            contract_id=contract_id,
            access_scope=access_scope,
            clause_id=clause_id,
        )

        if record is None:
            raise ContractClauseNotFoundError(
                "Contract clause was not found"
            )

        return self._clause_repository.to_domain(
            record
        )
