from app.rag.models import RetrievedChunk


def build_context(
    results: tuple[RetrievedChunk, ...],
) -> str:
    """Build traceable LLM context from retrieved chunks."""

    if not results:
        raise ValueError(
            "Cannot build context without retrieval results"
        )

    context_sections: list[str] = []

    for source_number, result in enumerate(
        results,
        start=1,
    ):
        citation_id = f"S{source_number}"

        structure = " > ".join(
            result.structure_path
        )

        section = (
            f"[{citation_id}]\n"
            f"Source: {result.source_id}, "
            f"version {result.source_version}\n"
            f"Location: {structure}\n"
            f"Pages: {result.page_start}"
            f"-{result.page_end}\n"
            f"Content:\n"
            f"{result.text}"
        )

        context_sections.append(section)

    return "\n\n".join(context_sections)