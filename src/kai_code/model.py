from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    """Minimal model metadata (TS parity: models.json in letta-code)."""

    id: str
    handle: str
    is_default: bool = False
    update_args: dict | None = None


_MODELS: list[ModelInfo] = [
    ModelInfo(id="sonnet-4.5", handle="anthropic:claude-sonnet-4-5-20250929", is_default=True),
    ModelInfo(id="gpt-4o", handle="openai:gpt-4o"),
    ModelInfo(id="gemini-2.0-flash", handle="google_genai:gemini-2.0-flash"),
]


def models() -> list[ModelInfo]:
    return list(_MODELS)


def resolve_model(model_identifier: str) -> str | None:
    for m in _MODELS:
        if m.id == model_identifier or m.handle == model_identifier:
            return m.handle
    return None


def get_default_model() -> str:
    for m in _MODELS:
        if m.is_default:
            return m.handle
    return _MODELS[0].handle


def format_available_models() -> str:
    return "\n".join([f"  {m.id:<20} {m.handle}" for m in _MODELS])


def get_model_info(model_identifier: str) -> ModelInfo | None:
    for m in _MODELS:
        if m.id == model_identifier or m.handle == model_identifier:
            return m
    return None


def get_model_update_args(model_identifier: str | None = None) -> dict | None:
    if not model_identifier:
        return None
    info = get_model_info(model_identifier)
    return info.update_args if info else None


# TypeScript-compat aliases
resolveModel = resolve_model
getDefaultModel = get_default_model
formatAvailableModels = format_available_models
getModelInfo = get_model_info
getModelUpdateArgs = get_model_update_args
