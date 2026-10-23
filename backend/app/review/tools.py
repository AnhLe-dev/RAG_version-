from collections.abc import Callable
from typing import Any
from uuid import UUID

from langchain_core.tools import StructuredTool

from app.contracts.clause_retrieval_service import (
    ContractClauseRetrievalService,
)
from app.db.session import SessionFactory
from app.knowledge import (
    KnowledgeRetrievalService,
    ReferenceClauseService,
)
from app.rag.ingestion.ucp600_corpus import (
    UCP600_SOURCE_ID,
    UCP600_SOURCE_VERSION,
)
from app.review.tool_schemas import (
    GetContractClausesInput,
    GetContractClausesOutput,
    GetReferenceClauseInput,
    GetReferenceClauseOutput,
    SearchKnowledgeInput,
    SearchKnowledgeOutput,
)


ToolFunction = Callable[..., dict[str, Any]]


def create_review_tools(
    *,
    session_factory: SessionFactory,
    knowledge_service: KnowledgeRetrievalService,
    reference_service: ReferenceClauseService,
    access_scope: str,
) -> tuple[StructuredTool, ...]:
    """Create contract review tools with a trusted access scope."""

    normalized_scope = access_scope.strip()

    if not normalized_scope:
        raise ValueError(
            "Access scope must not be empty"
        )

    def get_contract_clauses(
        contract_id: UUID,
        labels: tuple[str, ...],
    ) -> dict[str, Any]:
        """Load exact clauses from one ready contract."""

        with session_factory() as session:
            service = ContractClauseRetrievalService(
                session=session,
            )

            clauses = tuple(
                service.get_by_label(
                    contract_id=contract_id,
                    access_scope=normalized_scope,
                    label=label,
                )
                for label in labels
            )

        output = GetContractClausesOutput(
            contract_id=contract_id,
            clauses=clauses,
        )

        return output.model_dump(
            mode="json"
        )

    def search_knowledge(
        contract_id: UUID,
        clause_label: str,
        question: str,
    ) -> dict[str, Any]:
        """Find UCP 600 evidence for one stored clause."""

        with session_factory() as session:
            contract_service = (
                ContractClauseRetrievalService(
                    session=session,
                )
            )

            clause = contract_service.get_by_label(
                contract_id=contract_id,
                access_scope=normalized_scope,
                label=clause_label,
            )

        evidence = (
            knowledge_service.search_contract_clause(
                question=question,
                clause=clause,
                access_scope=normalized_scope,
                source_id=UCP600_SOURCE_ID,
                source_version=(
                    UCP600_SOURCE_VERSION
                ),
            )
        )

        output = SearchKnowledgeOutput(
            contract_id=contract_id,
            clause_id=clause.clause_id,
            clause_label=clause.label,
            evidence=evidence,
        )

        return output.model_dump(
            mode="json"
        )

    def get_reference_clause(
        article_number: int,
    ) -> dict[str, Any]:
        """Load one complete UCP 600 article."""

        reference_clause = (
            reference_service.get_article(
                source_id=UCP600_SOURCE_ID,
                source_version=(
                    UCP600_SOURCE_VERSION
                ),
                article_number=article_number,
                access_scope=normalized_scope,
            )
        )

        output = GetReferenceClauseOutput(
            reference_clause=reference_clause,
        )

        return output.model_dump(
            mode="json"
        )

    tool_functions: tuple[
        tuple[
            ToolFunction,
            str,
            str,
            type,
        ],
        ...,
    ] = (
        (
            get_contract_clauses,
            "get_contract_clauses",
            (
                "Read exact clauses from the selected "
                "contract. Use this before reviewing or "
                "quoting contract text. This tool does not "
                "assess compliance."
            ),
            GetContractClausesInput,
        ),
        (
            search_knowledge,
            "search_knowledge",
            (
                "Find candidate UCP 600 evidence for one "
                "stored contract clause and a legal question. "
                "A missing result does not prove that no "
                "relevant rule exists."
            ),
            SearchKnowledgeInput,
        ),
        (
            get_reference_clause,
            "get_reference_clause",
            (
                "Read the complete text of one UCP 600 "
                "Article after search identifies a relevant "
                "Article number. The number refers to UCP "
                "600, not to a contract clause."
            ),
            GetReferenceClauseInput,
        ),
    )

    return tuple(
        StructuredTool.from_function(
            func=function,
            name=name,
            description=description,
            args_schema=args_schema,
        )
        for (
            function,
            name,
            description,
            args_schema,
        ) in tool_functions
    )