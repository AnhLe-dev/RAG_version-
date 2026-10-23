from hashlib import sha256

from app.rag.models import (
    DocumentChunk,
    LegalArticle,
    LegalItem,
    LocatedTextBlock,
    SourceDocument,
    SourceSpan,
)

def _create_stable_id(*parts: str) -> str:
    """Create a deterministic SHA-256 identifier."""

    serialized_parts = "\x1f".join(parts)

    return sha256(
        serialized_parts.encode("utf-8")
    ).hexdigest()

def _group_blocks(
    blocks: tuple[LocatedTextBlock, ...],
    max_characters: int,
) -> tuple[tuple[LocatedTextBlock, ...], ...]:
    """Tại sao chia theo block?
    Mỗi block đã có page, bbox và block index. Nếu cắt giữa một block, citation chỉ còn chính xác gần đúng.."""

    if max_characters < 200:
        raise ValueError(
            "MAX_CHARACTERS must be at least 200"
        )

    groups: list[tuple[LocatedTextBlock, ...]] = []
    current_blocks: list[LocatedTextBlock] = []
    current_length = 0

    for block in blocks:
        block_text = block.text.strip()

        if len(block_text) > max_characters:
            raise ValueError(
                "A source block exceeds MAX_CHARACTERS; "
                f"page={block.page_number}, "
                f"block={block.block_index}, "
                f"characters={len(block_text)}"
            )

        separator_length = 1 if current_blocks else 0
        candidate_length = (
            current_length
            + separator_length
            + len(block_text)
        )

        if (
            current_blocks
            and candidate_length > max_characters
        ):
            groups.append(tuple(current_blocks))
            current_blocks = []
            current_length = 0

        if current_blocks:
            current_length += 1

        current_blocks.append(block)
        current_length += len(block_text)

    if current_blocks:
        groups.append(tuple(current_blocks))

    return tuple(groups)

def _create_structure_path(
    article: LegalArticle,
    item: LegalItem,
    part_index: int,
    part_count: int,
) -> tuple[str, ...]:
    """Create a human-readable legal structure path."""

    path = [
        f"Article {article.article_number}: {article.title}"
    ]

    if item.paragraph_label is not None:
        path.append(
            f"paragraph {item.paragraph_label}"
        )

    if item.label is not None:
        path.append(
            f"item {item.label}"
        )

    if part_count > 1:
        path.append(
            f"part {part_index + 1} of {part_count}"
        )

    return tuple(path)

def _create_source_spans(
    blocks: tuple[LocatedTextBlock, ...],
) -> tuple[SourceSpan, ...]:
    """Create citation spans from source blocks."""

    return tuple(
        SourceSpan(
            page_number=block.page_number,
            block_index=block.block_index,
            bbox=block.bbox,
        )
        for block in blocks
    )

def build_document_chunks(
    source: SourceDocument,
    articles: tuple[LegalArticle, ...],
    items: tuple[LegalItem, ...],
    *,
    max_characters: int,
) -> tuple[DocumentChunk, ...]:
    """Build deterministic, traceable chunks from legal items."""

    articles_by_number = {
        article.article_number: article
        for article in articles
    }

    chunks: list[DocumentChunk] = []

    for item in items:
        article = articles_by_number.get(
            item.article_number
        )

        if article is None:
            raise ValueError(
                f"Article {item.article_number} was not found"
            )

        block_groups = _group_blocks(
            item.content_blocks,
            max_characters,
        )

        paragraph_identity = (
            item.paragraph_label
            if item.paragraph_label is not None
            else "none"
        )
        item_identity = (
            item.label
            if item.label is not None
            else "none"
        )

        logical_parent_id = _create_stable_id(
            source.source_id,
            source.source_version,
            source.checksum_sha256,
            f"article:{item.article_number}",
            f"paragraph:{paragraph_identity}",
            f"item:{item_identity}",
        )

        for part_index, blocks in enumerate(block_groups):
            chunk_id = _create_stable_id(
                logical_parent_id,
                f"part:{part_index}",
            )

            chunk_text = "\n".join(
                block.text.strip()
                for block in blocks
            )

            source_spans = _create_source_spans(
                blocks
            )

            part_count = len(block_groups)

            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    source_id=source.source_id,
                    source_version=source.source_version,
                    source_checksum_sha256=(
                        source.checksum_sha256
                    ),
                    text=chunk_text,
                    article_number=item.article_number,
                    structure_path=_create_structure_path(
                        article,
                        item,
                        part_index,
                        part_count,
                    ),
                    page_start=min(
                        span.page_number
                        for span in source_spans
                    ),
                    page_end=max(
                        span.page_number
                        for span in source_spans
                    ),
                    source_spans=source_spans,
                    parent_chunk_id=(
                        logical_parent_id
                        if part_count > 1
                        else None
                    ),
                    access_scope=source.access_scope,
                )
            )

    chunk_ids = [
        chunk.chunk_id
        for chunk in chunks
    ]

    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError(
            "Duplicate chunk IDs were generated"
        )

    return tuple(chunks)