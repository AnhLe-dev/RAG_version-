import re


_CONTEXT_CITATION_PATTERN = re.compile(
    r"(?m)^\[(S[1-9]\d*)\]$"
)

_ANSWER_CITATION_PATTERN = re.compile(
    r"\[(S[1-9]\d*)\]"
)
# thêm citation đúng nội nó trả lời hay không ?

def _extract_unique_labels(
    pattern: re.Pattern[str],
    text: str,
) -> tuple[str, ...]:
    """Extract citation labels while preserving their order."""

    return tuple(
        dict.fromkeys(
            pattern.findall(text)
        )
    )


def validate_answer_citations(
    *,
    answer: str,
    context: str,
) -> tuple[str, ...]:
    """Validate citations used in a generated answer."""

    normalized_answer = answer.strip()
    normalized_context = context.strip()

    if not normalized_answer:
        raise ValueError(
            "Cannot validate an empty answer"
        )

    if not normalized_context:
        raise ValueError(
            "Cannot validate citations without context"
        )

    available_labels = _extract_unique_labels(
        _CONTEXT_CITATION_PATTERN,
        normalized_context,
    )

    if not available_labels:
        raise ValueError(
            "Context does not contain any citation labels"
        )

    used_labels = _extract_unique_labels(
        _ANSWER_CITATION_PATTERN,
        normalized_answer,
    )

    if not used_labels:
        raise ValueError(
            "Generated answer does not contain any citations"
        )

    unknown_labels = tuple(
        label
        for label in used_labels
        if label not in available_labels
    )

    if unknown_labels:
        raise ValueError(
            "Generated answer contains unknown citations: "
            f"{unknown_labels}"
        )

    return used_labels