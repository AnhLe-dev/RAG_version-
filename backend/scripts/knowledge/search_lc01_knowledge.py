from argparse import ArgumentParser
from uuid import UUID

from app.contracts.clause_retrieval_service import (
    ContractClauseRetrievalService,
)
from app.core.config import get_settings
from app.db.session import (
    create_database_engine,
    create_session_factory,
)
from app.knowledge import (
    create_knowledge_retrieval_service,
)


EXPECTED_ARTICLE_NUMBER = 16


def parse_arguments() -> tuple[UUID, str, str]:
    """Read the contract, clause label, and question."""

    parser = ArgumentParser(
        description=(
            "Find UCP 600 evidence for one LC01 clause"
        )
    )

    parser.add_argument(
        "contract_id",
        type=UUID,
    )
    parser.add_argument(
        "label",
        type=str,
    )
    parser.add_argument(
        "question",
        type=str,
    )

    arguments = parser.parse_args()

    return (
        arguments.contract_id,
        arguments.label,
        arguments.question,
    )


def main() -> None:
    """Retrieve UCP 600 evidence for one LC01 clause."""

    contract_id, label, question = parse_arguments()
    settings = get_settings()

    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)

    knowledge_service = None

    try:
        with session_factory() as session:
            contract_service = (
                ContractClauseRetrievalService(
                    session=session,
                )
            )

            clause = contract_service.get_by_label(
                contract_id=contract_id,
                access_scope="public",
                label=label,
            )

        knowledge_service = (
            create_knowledge_retrieval_service(
                settings
            )
        )

        results = (
            knowledge_service.search_contract_clause(
                question=question,
                clause=clause,
                access_scope="public",
                source_id="ucp600",
                source_version="1",
            )
        )

        if not results:
            raise RuntimeError(
                "Knowledge retrieval returned no evidence"
            )

        article_numbers = {
            result.article_number
            for result in results
        }

        if EXPECTED_ARTICLE_NUMBER not in article_numbers:
            raise RuntimeError(
                "Expected UCP 600 Article 16 was not "
                "found in the retrieved evidence"
            )

        print("LC01 knowledge retrieval passed")
        print(f"contract_id={contract_id}")
        print(f"clause_label={clause.label}")
        print(f"result_count={len(results)}")
        print(
            f"article_numbers="
            f"{sorted(article_numbers)}"
        )

        for rank, result in enumerate(
            results,
            start=1,
        ):
            print()
            print(f"result_rank={rank}")
            print(f"score={result.score:.6f}")
            print(f"chunk_id={result.chunk_id}")
            print(f"source_id={result.source_id}")
            print(
                f"source_version="
                f"{result.source_version}"
            )
            print(
                f"source_checksum_sha256="
                f"{result.source_checksum_sha256}"
            )
            print(
                f"article_number="
                f"{result.article_number}"
            )
            print(
                "structure_path="
                + " > ".join(
                    result.structure_path
                )
            )
            print(
                f"page_range="
                f"{result.page_start}-"
                f"{result.page_end}"
            )
            print(
                f"source_span_count="
                f"{len(result.source_spans)}"
            )
            print("text:")
            print(result.text)
            print("source_spans:")

            for span_index, span in enumerate(
                result.source_spans
            ):
                print(
                    f"span={span_index} "
                    f"page={span.page_number} "
                    f"block={span.block_index} "
                    f"bbox={span.bbox}"
                )
    finally:
        if knowledge_service is not None:
            knowledge_service.close()

        engine.dispose()


if __name__ == "__main__":
    main()