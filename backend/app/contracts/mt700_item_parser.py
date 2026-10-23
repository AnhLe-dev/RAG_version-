from dataclasses import dataclass, field
from re import compile as compile_pattern
from uuid import UUID, uuid4

from app.contracts.models import (
    ClauseKind,
    ContractClause,
    ContractSourceSpan,
)
from app.rag.models import ExtractedPage, PageTextBlock


_ITEM_START = compile_pattern(
    r"(?m)^[ \t]*(?P<number>\d{1,2})/[ \t]*"
)


@dataclass
class _ItemDraft:
    """Accumulate one numbered item across PDF blocks."""

    parent: ContractClause
    number: int
    position: int
    text_parts: list[str] = field(default_factory=list)
    source_spans: list[ContractSourceSpan] = field(
        default_factory=list
    )


def _build_block_lookup(
    pages: tuple[ExtractedPage, ...],
) -> dict[tuple[int, int], tuple[ExtractedPage, PageTextBlock]]:
    """Index blocks by their stable page and block identifiers."""

    return {
        (page.page_number, block.block_index): (
            page,
            block,
        )
        for page in pages
        for block in page.blocks
    }


def _finish_item(
    draft: _ItemDraft,
) -> ContractClause:
    """Convert one accumulated item into a domain model."""

    spans = tuple(draft.source_spans)

    return ContractClause(
        clause_id=uuid4(),
        contract_id=draft.parent.contract_id,
        parent_clause_id=draft.parent.clause_id,
        label=(
            f"{draft.parent.label}."
            f"{draft.number}"
        ),
        title=(
            f"{draft.parent.title} "
            f"item {draft.number}"
        ),
        raw_text="\n".join(draft.text_parts),
        kind=ClauseKind.SWIFT_ITEM,
        order_index=(
            draft.parent.order_index
            + draft.position
            + 1
        ),
        page_start=min(
            span.page_number
            for span in spans
        ),
        page_end=max(
            span.page_number
            for span in spans
        ),
        source_spans=spans,
    )


def parse_mt700_numbered_items(
    *,
    pages: tuple[ExtractedPage, ...],
    parent_fields: tuple[ContractClause, ...],
    item_field_labels: frozenset[str],
) -> tuple[ContractClause, ...]:
    """Parse numbered children of selected MT700 fields."""

    block_lookup = _build_block_lookup(pages)
    items: list[ContractClause] = []

    for parent in parent_fields:
        if parent.label not in item_field_labels:
            continue

        current_draft: _ItemDraft | None = None
        previous_number = 0
        item_position = 0

        for parent_span in parent.source_spans:
            lookup_key = (
                parent_span.page_number,
                parent_span.block_index,
            )
            page, block = block_lookup[lookup_key]
            matches = list(
                _ITEM_START.finditer(block.text)
            )

            if len(matches) > 1:
                raise ValueError(
                    "Multiple numbered items in one block "
                    "are not supported"
                )

            segment_start = 0

            if matches:
                if current_draft is not None:
                    items.append(
                        _finish_item(current_draft)
                    )

                item_number = int(
                    matches[0].group("number")
                )

                if item_number <= previous_number:
                    raise ValueError(
                        "MT700 item numbers must increase"
                    )

                current_draft = _ItemDraft(
                    parent=parent,
                    number=item_number,
                    position=item_position,
                )
                previous_number = item_number
                item_position += 1
                segment_start = matches[0].start()

            if current_draft is None:
                continue

            segment_end = len(block.text)
            segment_text = block.text[
                segment_start:segment_end
            ].strip()

            if not segment_text:
                continue

            current_draft.text_parts.append(
                segment_text
            )
            current_draft.source_spans.append(
                ContractSourceSpan(
                    page_number=page.page_number,
                    block_index=block.block_index,
                    bbox=block.bbox,
                    page_width=page.width,
                    page_height=page.height,
                    char_start=segment_start,
                    char_end=segment_end,
                )
            )

        if current_draft is not None:
            items.append(
                _finish_item(current_draft)
            )

    return tuple(items)
