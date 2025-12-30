from importlib import metadata
from typing import TYPE_CHECKING

try:
    __version__ = metadata.version("kai-code")
except Exception:  # pragma: no cover
    __version__ = "0.0.0"

# Core agent imports - require deepagents dependency
# These are optional to allow error framework to be used independently
try:
    from .agent import KaiAgent, KaiAgentConfig, KaiResult
    from .client import KaiClient, getClient, get_client
    from .create import CreateAgentResult, createAgent, create_agent
    from .headless import handleHeadlessCommand, handle_headless_command
    from .model import (
        ModelInfo,
        format_available_models,
        formatAvailableModels,
        get_default_model,
        getDefaultModel,
        get_model_info,
        getModelInfo,
        get_model_update_args,
        getModelUpdateArgs,
        models,
        resolve_model,
        resolveModel,
    )
    from .modify import (
        LinkResult,
        SystemPromptUpdateResult,
        UnlinkResult,
        link_tools_to_agent,
        unlink_tools_from_agent,
        update_agent_llm_config,
        update_agent_system_prompt,
        updateAgentLLMConfig,
        linkToolsToAgent,
        unlinkToolsFromAgent,
        updateAgentSystemPrompt,
    )
    from .permissions import PermissionConfig
    from .permission_mode import (
        PermissionMode,
        VALID_PERMISSION_MODES,
        PermissionModeResolution,
        resolve_permission_mode,
    )
    from .project_settings import KaiProjectSettings
except ImportError:  # pragma: no cover
    # Core agent functionality not available - likely missing deepagents
    # Error framework can still be used independently
    KaiAgent = None  # type: ignore[misc, assignment]
    KaiAgentConfig = None  # type: ignore[misc, assignment]
    KaiResult = None  # type: ignore[misc, assignment]
    KaiClient = None  # type: ignore[misc, assignment]
    getClient = None  # type: ignore[misc, assignment]
    get_client = None  # type: ignore[misc, assignment]
    CreateAgentResult = None  # type: ignore[misc, assignment]
    createAgent = None  # type: ignore[misc, assignment]
    create_agent = None  # type: ignore[misc, assignment]
    handleHeadlessCommand = None  # type: ignore[misc, assignment]
    handle_headless_command = None  # type: ignore[misc, assignment]
    ModelInfo = None  # type: ignore[misc, assignment]
    format_available_models = None  # type: ignore[misc, assignment]
    formatAvailableModels = None  # type: ignore[misc, assignment]
    get_default_model = None  # type: ignore[misc, assignment]
    getDefaultModel = None  # type: ignore[misc, assignment]
    get_model_info = None  # type: ignore[misc, assignment]
    getModelInfo = None  # type: ignore[misc, assignment]
    get_model_update_args = None  # type: ignore[misc, assignment]
    getModelUpdateArgs = None  # type: ignore[misc, assignment]
    models = None  # type: ignore[misc, assignment]
    resolve_model = None  # type: ignore[misc, assignment]
    resolveModel = None  # type: ignore[misc, assignment]
    LinkResult = None  # type: ignore[misc, assignment]
    SystemPromptUpdateResult = None  # type: ignore[misc, assignment]
    UnlinkResult = None  # type: ignore[misc, assignment]
    link_tools_to_agent = None  # type: ignore[misc, assignment]
    unlink_tools_from_agent = None  # type: ignore[misc, assignment]
    update_agent_llm_config = None  # type: ignore[misc, assignment]
    update_agent_system_prompt = None  # type: ignore[misc, assignment]
    updateAgentLLMConfig = None  # type: ignore[misc, assignment]
    linkToolsToAgent = None  # type: ignore[misc, assignment]
    unlinkToolsFromAgent = None  # type: ignore[misc, assignment]
    updateAgentSystemPrompt = None  # type: ignore[misc, assignment]
    PermissionConfig = None  # type: ignore[misc, assignment]
    PermissionMode = None  # type: ignore[misc, assignment]
    VALID_PERMISSION_MODES = None  # type: ignore[misc, assignment]
    PermissionModeResolution = None  # type: ignore[misc, assignment]
    resolve_permission_mode = None  # type: ignore[misc, assignment]
    KaiProjectSettings = None  # type: ignore[misc, assignment]

# Error framework for actionable error messages
from .errors import (
    ActionableError,
    ActionableErrorException,
    ErrorRenderer,
    ErrorType,
    render_error,
)
from .error_suggestions import (
    # Fuzzy matching utilities
    similar_strings,
    suggest_commands,
    suggest_files,
    suggest_flags,
    suggest_values,
    # File error builders
    make_file_not_found_error,
    make_file_permission_error,
    make_invalid_file_type_error,
    # Command error builders
    make_unknown_command_error,
    make_invalid_flag_error,
    make_missing_argument_error,
    # Configuration error builders
    make_api_key_missing_error,
    make_model_not_available_error,
    make_skill_not_found_error,
    # DBT error builders
    make_dbt_connection_error,
    make_dbt_model_not_found_error,
    make_dbt_command_error,
    # Provider constants
    PROVIDER_API_KEY_INSTRUCTIONS,
)

# Optional dbt agent - requires dbt extra
try:
    from .agents.dbt import DbtAgent
except (ImportError, TypeError):  # TypeError for Python <3.10 type syntax
    DbtAgent = None  # type: ignore[misc, assignment]

__all__ = [
    "__version__",
    "KaiAgent",
    "KaiAgentConfig",
    "KaiResult",
    "KaiClient",
    "get_client",
    "getClient",
    "CreateAgentResult",
    "create_agent",
    "createAgent",
    "handle_headless_command",
    "handleHeadlessCommand",
    "ModelInfo",
    "models",
    "resolve_model",
    "resolveModel",
    "get_default_model",
    "getDefaultModel",
    "format_available_models",
    "formatAvailableModels",
    "get_model_info",
    "getModelInfo",
    "get_model_update_args",
    "getModelUpdateArgs",
    "update_agent_llm_config",
    "update_agent_system_prompt",
    "link_tools_to_agent",
    "unlink_tools_from_agent",
    "LinkResult",
    "UnlinkResult",
    "SystemPromptUpdateResult",
    "updateAgentLLMConfig",
    "linkToolsToAgent",
    "unlinkToolsFromAgent",
    "updateAgentSystemPrompt",
    "PermissionConfig",
    "PermissionMode",
    "VALID_PERMISSION_MODES",
    "PermissionModeResolution",
    "resolve_permission_mode",
    "KaiProjectSettings",
    # Error framework
    "ActionableError",
    "ActionableErrorException",
    "ErrorRenderer",
    "ErrorType",
    "render_error",
    # Fuzzy matching utilities
    "similar_strings",
    "suggest_commands",
    "suggest_files",
    "suggest_flags",
    "suggest_values",
    # Error builder functions
    "make_file_not_found_error",
    "make_file_permission_error",
    "make_invalid_file_type_error",
    "make_unknown_command_error",
    "make_invalid_flag_error",
    "make_missing_argument_error",
    "make_api_key_missing_error",
    "make_model_not_available_error",
    "make_skill_not_found_error",
    "make_dbt_connection_error",
    "make_dbt_model_not_found_error",
    "make_dbt_command_error",
    "PROVIDER_API_KEY_INSTRUCTIONS",
    # dbt agent (optional)
    "DbtAgent",
]
