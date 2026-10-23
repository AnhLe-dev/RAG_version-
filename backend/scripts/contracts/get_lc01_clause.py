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


def parse_arguments() -> tuple[UUID, str]:
    """Read the contract ID and clause label."""

    parser = ArgumentParser()
    parser.add_argument(
        "contract_id",
        type=UUID,
    )
    parser.add_argument(
        "label",
        type=str,
    )

    arguments = parser.parse_args()

    return arguments.contract_id, arguments.label


def main() -> None:
    """Retrieve and display one LC01 clause."""

    contract_id, label = parse_arguments()
    settings = get_settings()
    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)

    try:
        with session_factory() as session:
            service = ContractClauseRetrievalService(
                session=session,
            )

            clause = service.get_by_label(
                contract_id=contract_id,
                access_scope="public",
                label=label,
            )

            print("Clause retrieval passed")
            print(f"label={clause.label}")
            print(f"title={clause.title}")
            print(f"kind={clause.kind.value}")
            print(
                f"page_range="
                f"{clause.page_start}-"
                f"{clause.page_end}"
            )
            print(
                f"source_span_count="
                f"{len(clause.source_spans)}"
            )
            print("raw_text:")
            print(clause.raw_text)
            print("source_spans:")

            for span_index, span in enumerate(
                clause.source_spans
            ):
                print(
                    f"span={span_index} "
                    f"page={span.page_number} "
                    f"block={span.block_index} "
                    f"bbox={span.bbox} "
                    f"chars={span.char_start}:{span.char_end}"
                )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
