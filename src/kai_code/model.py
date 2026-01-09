from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from importlib import resources
from typing import Callable


# Default context window size (128K tokens) when model limit is unknown
DEFAULT_CONTEXT_WINDOW = 128000


@dataclass(frozen=True)
class ModelInfo:
    """Minimal model metadata (TS parity: models.json in letta-code)."""

    id: str
    handle: str
    provider: str = ""
    is_default: bool = False
    update_args: dict | None = None
    context_window: int | None = None


def _load_models_json() -> list[ModelInfo] | None:
    """Load static fallback models from JSON."""
    try:
        data = resources.files(__package__).joinpath("models.json").read_text()
        raw = json.loads(data)
        if not isinstance(raw, list):
            return None
        out: list[ModelInfo] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            mid = item.get("id")
            handle = item.get("handle")
            if not isinstance(mid, str) or not isinstance(handle, str):
                continue
            provider = handle.split(":")[0] if ":" in handle else ""
            context_window = item.get("context_window")
            out.append(
                ModelInfo(
                    id=mid,
                    handle=handle,
                    provider=provider,
                    is_default=bool(item.get("is_default", False)),
                    update_args=item.get("update_args") if isinstance(item.get("update_args"), dict) else None,
                    context_window=context_window if isinstance(context_window, int) else None,
                )
            )
        return out or None
    except Exception:
        return None


def _fetch_anthropic_models() -> list[ModelInfo]:
    """Fetch available models from Anthropic API."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return []

    try:
        import httpx
        response = httpx.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            timeout=10.0,
        )
        if response.status_code != 200:
            return []

        data = response.json()
        models_list = []
        for model in data.get("data", []):
            model_id = model.get("id", "")
            if not model_id:
                continue

            # Create friendly ID (e.g., "claude-sonnet-4" -> "sonnet-4")
            friendly_id = model_id
            if friendly_id.startswith("claude-"):
                friendly_id = friendly_id[7:]  # Remove "claude-" prefix
            # Simplify version suffixes
            parts = friendly_id.split("-")
            if len(parts) > 2 and parts[-1].isdigit() and len(parts[-1]) == 8:
                friendly_id = "-".join(parts[:-1])

            models_list.append(ModelInfo(
                id=friendly_id,
                handle=f"anthropic:{model_id}",
                provider="anthropic",
            ))

        return models_list
    except Exception:
        return []


def _fetch_openai_models() -> list[ModelInfo]:
    """Fetch available models from OpenAI API."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return []

    try:
        import httpx
        response = httpx.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        if response.status_code != 200:
            return []

        data = response.json()
        models_list = []
        # Filter to chat-capable models
        chat_models = {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "o1", "o1-mini", "o3-mini"}

        for model in data.get("data", []):
            model_id = model.get("id", "")
            if not model_id:
                continue

            # Only include known chat models (skip fine-tuned, embedding, etc.)
            base_id = model_id.split("-")[0] + "-" + model_id.split("-")[1] if "-" in model_id else model_id
            if not any(model_id.startswith(m) for m in chat_models):
                continue

            # Use the model ID directly as friendly ID
            friendly_id = model_id

            models_list.append(ModelInfo(
                id=friendly_id,
                handle=f"openai:{model_id}",
                provider="openai",
            ))

        return models_list
    except Exception:
        return []


def _fetch_google_models() -> list[ModelInfo]:
    """Fetch available models from Google AI API."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return []

    try:
        import httpx
        response = httpx.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
            timeout=10.0,
        )
        if response.status_code != 200:
            return []

        data = response.json()
        models_list = []

        for model in data.get("models", []):
            model_name = model.get("name", "")
            if not model_name:
                continue

            # Extract model ID from name (e.g., "models/gemini-2.0-flash" -> "gemini-2.0-flash")
            model_id = model_name.split("/")[-1] if "/" in model_name else model_name

            # Only include generative models
            supported = model.get("supportedGenerationMethods", [])
            if "generateContent" not in supported:
                continue

            models_list.append(ModelInfo(
                id=model_id,
                handle=f"google_genai:{model_id}",
                provider="google_genai",
            ))

        return models_list
    except Exception:
        return []


def _fetch_openrouter_models() -> list[ModelInfo]:
    """Fetch available models from OpenRouter API."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return []

    try:
        import httpx
        response = httpx.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        if response.status_code != 200:
            return []

        data = response.json()
        models_list = []

        for model in data.get("data", []):
            model_id = model.get("id", "")
            if not model_id:
                continue

            # Get context length if available
            context_length = model.get("context_length")

            # Create friendly ID (e.g., "anthropic/claude-3.5-sonnet" -> "or-claude-3.5-sonnet")
            friendly_id = model_id
            if "/" in friendly_id:
                # Extract just the model name after the provider prefix
                friendly_id = "or-" + friendly_id.split("/")[-1]

            models_list.append(ModelInfo(
                id=friendly_id,
                handle=f"openrouter:{model_id}",
                provider="openrouter",
                context_window=context_length if isinstance(context_length, int) else None,
            ))

        return models_list
    except Exception:
        return []


# Cache for dynamic models
_MODELS_CACHE: list[ModelInfo] | None = None
_MODELS_CACHE_TIME: float = 0
_MODELS_CACHE_TTL: float = 300  # 5 minutes

# Static fallback models
_STATIC_MODELS: list[ModelInfo] = _load_models_json() or [
    ModelInfo(id="sonnet-4.5", handle="anthropic:claude-sonnet-4-5-20250929", provider="anthropic", context_window=200000),
    ModelInfo(id="gpt-4o", handle="openai:gpt-4o", provider="openai", context_window=128000),
    ModelInfo(id="gemini-2.0-flash", handle="google_genai:gemini-2.0-flash", provider="google_genai", is_default=True, context_window=1048576),
]


def _refresh_models_cache() -> None:
    """Refresh the models cache from APIs."""
    global _MODELS_CACHE, _MODELS_CACHE_TIME

    all_models: list[ModelInfo] = []

    # Fetch from each provider
    all_models.extend(_fetch_anthropic_models())
    all_models.extend(_fetch_openai_models())
    all_models.extend(_fetch_google_models())
    all_models.extend(_fetch_openrouter_models())

    if all_models:
        # Set default if not set
        has_default = any(m.is_default for m in all_models)
        if not has_default and all_models:
            # Make gemini-2.0-flash default if available, otherwise first model
            for i, m in enumerate(all_models):
                if "gemini-2.0-flash" in m.id:
                    all_models[i] = ModelInfo(
                        id=m.id,
                        handle=m.handle,
                        provider=m.provider,
                        is_default=True,
                        update_args=m.update_args,
                        context_window=m.context_window,
                    )
                    has_default = True
                    break
            if not has_default:
                m = all_models[0]
                all_models[0] = ModelInfo(
                    id=m.id,
                    handle=m.handle,
                    provider=m.provider,
                    is_default=True,
                    update_args=m.update_args,
                    context_window=m.context_window,
                )

        _MODELS_CACHE = all_models
        _MODELS_CACHE_TIME = time.time()


def models(use_cache: bool = True, force_refresh: bool = False) -> list[ModelInfo]:
    """Get available models.

    Args:
        use_cache: Use cached results if available
        force_refresh: Force refresh from APIs

    Returns:
        List of available models
    """
    global _MODELS_CACHE, _MODELS_CACHE_TIME

    # Check if we need to refresh
    if force_refresh or _MODELS_CACHE is None or (time.time() - _MODELS_CACHE_TIME > _MODELS_CACHE_TTL):
        _refresh_models_cache()

    # Return cached or static fallback
    if _MODELS_CACHE:
        return list(_MODELS_CACHE)

    return list(_STATIC_MODELS)


def models_static() -> list[ModelInfo]:
    """Get static fallback models (no API calls)."""
    return list(_STATIC_MODELS)


def resolve_model(model_identifier: str) -> str | None:
    """Resolve a model identifier to its full handle."""
    # First try cached/API models
    for m in models():
        if m.id == model_identifier or m.handle == model_identifier:
            return m.handle
    # Fall back to static models
    for m in _STATIC_MODELS:
        if m.id == model_identifier or m.handle == model_identifier:
            return m.handle
    # If it looks like a full handle, return it directly
    if ":" in model_identifier:
        return model_identifier
    return None


def get_default_model() -> str:
    """Get the default model handle."""
    # First check cached/API models
    for m in models():
        if m.is_default:
            return m.handle
    # Fall back to static models
    for m in _STATIC_MODELS:
        if m.is_default:
            return m.handle
    # Last resort
    all_models = models()
    if all_models:
        return all_models[0].handle
    return _STATIC_MODELS[0].handle


def format_available_models() -> str:
    """Format available models for display."""
    return "\n".join([f"  {m.id:<20} {m.handle}" for m in models()])


def get_model_info(model_identifier: str) -> ModelInfo | None:
    """Get model info by identifier."""
    for m in models():
        if m.id == model_identifier or m.handle == model_identifier:
            return m
    for m in _STATIC_MODELS:
        if m.id == model_identifier or m.handle == model_identifier:
            return m
    return None


def get_model_update_args(model_identifier: str | None = None) -> dict | None:
    """Get model-specific update args."""
    if not model_identifier:
        return None
    info = get_model_info(model_identifier)
    return info.update_args if info else None


def get_context_limit(model_identifier: str) -> int:
    """Get the context window limit for a model.

    Args:
        model_identifier: Model ID or handle (e.g., "sonnet-4.5" or "anthropic:claude-sonnet-4-5-20250929")

    Returns:
        Context window size in tokens. Returns DEFAULT_CONTEXT_WINDOW (128K) if unknown.
    """
    info = get_model_info(model_identifier)
    if info and info.context_window:
        return info.context_window
    return DEFAULT_CONTEXT_WINDOW


def refresh_models() -> list[ModelInfo]:
    """Force refresh models from APIs."""
    return models(force_refresh=True)


# TypeScript-compat aliases
resolveModel = resolve_model
getDefaultModel = get_default_model
formatAvailableModels = format_available_models
getModelInfo = get_model_info
getModelUpdateArgs = get_model_update_args
getContextLimit = get_context_limit
