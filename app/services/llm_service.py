"""
LLM service — provider abstraction for LangChain-based agents.

Handles model resolution, API key validation, and LLM instance caching.
The agent layer (agent_service.py) calls get_llm_for_agent() to obtain
a configured LLM, then builds its own tool-calling agent on top.
"""

from dataclasses import dataclass
from functools import lru_cache

from fastapi import HTTPException, status
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import settings

# ---------------------------------------------------------------------------
# Supported providers
# ---------------------------------------------------------------------------

PROVIDER_GEMINI = "gemini"
PROVIDER_OPENAI = "openai"
PROVIDER_ANTHROPIC = "anthropic"

SUPPORTED_PROVIDERS = {PROVIDER_GEMINI, PROVIDER_OPENAI, PROVIDER_ANTHROPIC}


# ---------------------------------------------------------------------------
# Response types
# ---------------------------------------------------------------------------


@dataclass
class LLMResponse:
    content: str
    model: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass
class LLMStreamChunk:
    """Yielded during streaming. `done=True` on the final chunk with full metadata."""

    content: str
    done: bool = False
    model: str = ""
    latency_ms: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_llm_for_agent(model: str | None = None) -> BaseChatModel:
    """Return a configured LLM instance suitable for tool-calling agents."""
    model_str = _resolve_and_validate(model)
    provider, model_name = _parse_model_str(model_str)
    return _get_llm_model(provider, model_name)


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------


@lru_cache
def _get_llm_model(provider: str, model_name: str) -> BaseChatModel:
    if provider == PROVIDER_GEMINI:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=settings.llm_temperature,
            api_key=settings.google_api_key,
        )
    if provider == PROVIDER_OPENAI:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_name,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key,
        )
    if provider == PROVIDER_ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model_name,
            temperature=settings.llm_temperature,
            api_key=settings.anthropic_api_key,
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported LLM provider: '{provider}'. Supported: {sorted(SUPPORTED_PROVIDERS)}",
    )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _resolve_and_validate(model: str | None) -> str:
    model_str = _resolve_model_str(model)
    if model_str not in settings.llm_allowed_models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{model_str}' is not in the allowed models list",
        )
    provider, _ = _parse_model_str(model_str)
    _check_api_key(provider)
    return model_str


def _resolve_model_str(model: str | None) -> str:
    """Return the model string to use, falling back to the configured default."""
    if model and model.strip():
        return model.strip()
    return settings.default_llm_model


def _parse_model_str(model_str: str) -> tuple[str, str]:
    """
    Parse 'provider/model-name' into (provider, model_name).
    Raises 400 if the format is wrong or the provider is unsupported.
    """
    if "/" not in model_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid model format '{model_str}'. "
                "Expected 'provider/model-name', e.g. 'gemini/gemini-2.5-flash'."
            ),
        )
    provider, model_name = model_str.split("/", 1)
    provider = provider.strip().lower()
    model_name = model_name.strip()
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider '{provider}'. Supported: {sorted(SUPPORTED_PROVIDERS)}",
        )
    return provider, model_name


def _check_api_key(provider: str) -> None:
    key_map = {
        PROVIDER_GEMINI: settings.google_api_key,
        PROVIDER_OPENAI: settings.openai_api_key,
        PROVIDER_ANTHROPIC: settings.anthropic_api_key,
    }
    if not key_map.get(provider):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"API key for provider '{provider}' is not configured",
        )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _string_content(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts).strip()
    return str(content).strip()
