from langchain_core.prompt_values import (
    ChatPromptValue,
)
from langchain_openai import ChatOpenAI

from app.core.config import Settings


def create_answer_model(
    settings: Settings,
) -> ChatOpenAI:
    """Create the configured answer generation model."""

    return ChatOpenAI(
        model=settings.default_llm_model,
        api_key=(
            settings.openai_api_key.get_secret_value()
        ),
        temperature=0,
        max_completion_tokens=600,
        max_retries=settings.max_retry_count,
        timeout=60,
    )


def generate_answer(
    *,
    prompt: ChatPromptValue,
    model: ChatOpenAI,
) -> str:
    """Generate and validate one grounded answer."""

    response = model.invoke(prompt)

    answer = response.text.strip()

    if not answer:
        raise ValueError(
            "The language model returned an empty answer"
        )

    return answer