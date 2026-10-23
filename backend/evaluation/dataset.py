import json
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from evaluation.schemas import (
    EvaluationCase,
    ReviewStatus,
)


_PLACEHOLDER_PATTERN = re.compile(
    r"(<[^>]+>|\bTODO\b|\bTBD\b|\bPLACEHOLDER\b)",
    flags=re.IGNORECASE,
)


class DatasetValidationError(ValueError):
    """Report an invalid evaluation dataset with source context."""


def _parse_json_line(
    *,
    raw_line: str,
    path: Path,
    line_number: int,
) -> dict[str, Any]:
    """Parse one JSONL line and require a JSON object."""

    try:
        value = json.loads(raw_line)
    except json.JSONDecodeError as error:
        raise DatasetValidationError(
            f"{path}:{line_number}: invalid JSON: "
            f"{error.msg}"
        ) from error

    if not isinstance(value, dict):
        raise DatasetValidationError(
            f"{path}:{line_number}: "
            "each JSONL line must contain one object"
        )

    return value


def _validate_case(
    *,
    raw_case: dict[str, Any],
    path: Path,
    line_number: int,
    allow_draft: bool,
) -> EvaluationCase:
    """Validate one raw object and enforce evaluation-only rules."""

    try:
        case = EvaluationCase.model_validate(
            raw_case
        )
    except ValidationError as error:
        raise DatasetValidationError(
            f"{path}:{line_number}: "
            f"invalid evaluation case: {error}"
        ) from error

    candidate_texts = (
        case.user_input,
        case.reference,
        *case.reference_contexts,
        *case.reference_evidence_ids,
    )

    if any(
        _PLACEHOLDER_PATTERN.search(value)
        for value in candidate_texts
    ):
        raise DatasetValidationError(
            f"{path}:{line_number}: "
            "placeholder values are not allowed"
        )

    if (
        not allow_draft
        and case.review_status is ReviewStatus.DRAFT
    ):
        raise DatasetValidationError(
            f"{path}:{line_number}: "
            f"case {case.case_id} is still draft"
        )

    return case


def load_evaluation_dataset(
    path: Path,
    *,
    allow_draft: bool = False,
) -> tuple[EvaluationCase, ...]:
    """Load and validate an evaluation dataset from JSONL."""

    if not path.is_file():
        raise DatasetValidationError(
            f"Dataset file does not exist: {path}"
        )

    cases: list[EvaluationCase] = []
    case_id_lines: dict[str, int] = {}

    with path.open(
        "r",
        encoding="utf-8",
    ) as dataset_file:
        for line_number, raw_line in enumerate(
            dataset_file,
            start=1,
        ):
            stripped_line = raw_line.strip()

            if not stripped_line:
                raise DatasetValidationError(
                    f"{path}:{line_number}: "
                    "blank lines are not allowed"
                )

            raw_case = _parse_json_line(
                raw_line=stripped_line,
                path=path,
                line_number=line_number,
            )

            case = _validate_case(
                raw_case=raw_case,
                path=path,
                line_number=line_number,
                allow_draft=allow_draft,
            )

            previous_line = case_id_lines.get(
                case.case_id
            )

            if previous_line is not None:
                raise DatasetValidationError(
                    f"{path}:{line_number}: "
                    f"duplicate case_id {case.case_id}; "
                    f"first declared on line {previous_line}"
                )

            case_id_lines[case.case_id] = (
                line_number
            )
            cases.append(case)

    if not cases:
        raise DatasetValidationError(
            f"Dataset must contain at least one case: {path}"
        )

    return tuple(cases)