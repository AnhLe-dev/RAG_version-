from dataclasses import dataclass
from re import fullmatch
from uuid import UUID, uuid4

from app.contracts.models import (
    ClauseKind,
    ContractClause,
    ContractSourceSpan,
)
from app.rag.models import ExtractedPage, PageTextBlock


_NOISE_VALUES = {
    "messages.pdf_cover_qr_code_label",
    "messages.downloaded_by",
}


@dataclass(frozen=True)
class _LocatedBlock:
    """Keep a PDF block together with its page metadata."""

    page: ExtractedPage
    block: PageTextBlock


def _is_noise_block(block: PageTextBlock) -> bool:
    """Identify known export metadata outside the MT700 content."""

    text = block.text.strip()

    return (
        text in _NOISE_VALUES
        or text.startswith("lOMoARcPSD|")
    )


def _parse_field_heading(
    text: str,
) -> tuple[str, str] | None:
    """Parse an MT700 field label and title from one block."""

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines or fullmatch(r"\d{2}", lines[0]) is None:
        return None

    field_number = lines[0]
    cursor = 1
    option = ""

    if (
        cursor < len(lines)
        and fullmatch(r"[A-Z]", lines[cursor])
        is not None
    ):
        option = lines[cursor]
        cursor += 1

    title_parts: list[str] = []

    for line in lines[cursor:]:
        if line.startswith(":"):
            break

        if ":" in line:
            title_part = line.split(":", 1)[0].strip()

            if title_part:
                title_parts.append(title_part)

            break

        title_parts.append(line)

    if not title_parts:
        return None

    label = f"{field_number}{option}"
    title = " ".join(title_parts)

    return label, title


def _build_clause(
    *,
    contract_id: UUID,
    label: str,
    title: str,
    order_index: int,
    located_blocks: list[_LocatedBlock],
) -> ContractClause:
    """Build one traceable MT700 field."""

    source_spans = tuple(
        ContractSourceSpan(
            page_number=located.page.page_number,
            block_index=located.block.block_index,
            bbox=located.block.bbox,
            page_width=located.page.width,
            page_height=located.page.height,
        )
        for located in located_blocks
    )

    raw_text = "\n".join(
        located.block.text
        for located in located_blocks
    )

    return ContractClause(
        clause_id=uuid4(),
        contract_id=contract_id,
        label=label,
        title=title,
        raw_text=raw_text,
        kind=ClauseKind.SWIFT_FIELD,
        order_index=order_index,
        page_start=min(
            span.page_number
            for span in source_spans
        ),
        page_end=max(
            span.page_number
            for span in source_spans
        ),
        source_spans=source_spans,
    )


def parse_mt700_fields(
    *,
    contract_id: UUID,
    pages: tuple[ExtractedPage, ...],
    selected_page_numbers: frozenset[int],
) -> tuple[ContractClause, ...]:
    """Parse ordered MT700 blocks into top-level fields."""

    clauses: list[ContractClause] = []

    current_label: str | None = None
    current_title: str | None = None
    current_blocks: list[_LocatedBlock] = []

    def finish_current_field() -> None:
        nonlocal current_label
        nonlocal current_title
        nonlocal current_blocks

        if (
            current_label is None
            or current_title is None
            or not current_blocks
        ):
            return

        clauses.append(
            _build_clause(
                contract_id=contract_id,
                label=current_label,
                title=current_title,
                order_index=len(clauses) * 100,
                located_blocks=current_blocks,
            )
        )

        current_label = None
        current_title = None
        current_blocks = []

    for page in pages:
        if page.page_number not in selected_page_numbers:
            continue

        for block in page.blocks:
            if _is_noise_block(block):
                continue

            heading = _parse_field_heading(block.text)

            if heading is not None:
                finish_current_field()
                current_label, current_title = heading
                current_blocks = [
                    _LocatedBlock(
                        page=page,
                        block=block,
                    )
                ]
                continue

            if current_label is not None:
                current_blocks.append(
                    _LocatedBlock(
                        page=page,
                        block=block,
                    )
                )

    finish_current_field()

    return tuple(clauses)
