from app.core.config import Settings
from app.rag.ingestion.ucp600_corpus import (
    PreparedCorpus,
    prepare_ucp600_corpus,
)
from app.rag.models import (
    LegalArticle,
    ReferenceClause,
    SourceSpan,
)


class KnowledgeSourceNotFoundError(LookupError):
    """Raised when a knowledge source is unavailable."""


class ReferenceClauseNotFoundError(LookupError):
    """Raised when a reference clause does not exist."""


class ReferenceClauseService:
    """Retrieve complete clauses from a prepared knowledge source."""

    def __init__(
        self,
        *,
        corpus: PreparedCorpus,
    ) -> None:
        self._corpus = corpus
        self._articles_by_number = {
            article.article_number: article
            for article in corpus.articles
        }

    def _require_source(
        self,
        *,
        source_id: str,
        source_version: str,
        access_scope: str,
    ) -> None:
        """Validate source identity and access scope."""

        normalized_source_id = source_id.strip()
        normalized_source_version = (
            source_version.strip()
        )
        normalized_scope = access_scope.strip()

        if not normalized_source_id:
            raise ValueError(
                "Source ID must not be empty"
            )

        if not normalized_source_version:
            raise ValueError(
                "Source version must not be empty"
            )

        if not normalized_scope:
            raise ValueError(
                "Access scope must not be empty"
            )

        source = self._corpus.source

        if (
            source.source_id != normalized_source_id
            or source.source_version
            != normalized_source_version
            or source.access_scope != normalized_scope
        ):
            raise KnowledgeSourceNotFoundError(
                "Knowledge source was not found"
            )

    @staticmethod
    def _build_source_spans(
        article: LegalArticle,
    ) -> tuple[SourceSpan, ...]:
        """Build ordered spans for the heading and article body."""

        blocks = (
            article.heading,
            *article.content_blocks,
        )

        block_keys = [
            (
                block.page_number,
                block.block_index,
            )
            for block in blocks
        ]

        if len(block_keys) != len(set(block_keys)):
            raise ValueError(
                "Reference article contains duplicate "
                "source blocks"
            )

        return tuple(
            SourceSpan(
                page_number=block.page_number,
                block_index=block.block_index,
                bbox=block.bbox,
            )
            for block in blocks
        )

    def get_article(
        self,
        *,
        source_id: str,
        source_version: str,
        article_number: int,
        access_scope: str,
    ) -> ReferenceClause:
        """Return one complete traceable UCP 600 article."""

        self._require_source(
            source_id=source_id,
            source_version=source_version,
            access_scope=access_scope,
        )

        article = self._articles_by_number.get(
            article_number
        )

        if article is None:
            raise ReferenceClauseNotFoundError(
                "Reference clause was not found"
            )

        source_spans = self._build_source_spans(
            article
        )
        span_pages = {
            span.page_number
            for span in source_spans
        }

        source = self._corpus.source

        return ReferenceClause(
            source_id=source.source_id,
            source_version=source.source_version,
            source_checksum_sha256=(
                source.checksum_sha256
            ),
            article_number=article.article_number,
            title=article.title,
            raw_text=article.text,
            page_start=min(span_pages),
            page_end=max(span_pages),
            source_spans=source_spans,
            access_scope=source.access_scope,
        )


def create_ucp600_reference_service(
    settings: Settings,
) -> ReferenceClauseService:
    """Prepare UCP 600 once and create its reference service."""

    return ReferenceClauseService(
        corpus=prepare_ucp600_corpus(settings)
    )