from __future__ import annotations

import enum
import logging
import os

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from dragonglass import paths

logger = logging.getLogger(__name__)


class LLMBackend(enum.StrEnum):
    litellm = "litellm"
    opencode = "opencode"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        toml_file=[paths.CONFIG_FILE, "config.toml"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls),
        )

    obsidian_dir: str = ""
    llm_model: str = "ollama/llama3.2"
    llm_backend: LLMBackend = LLMBackend.litellm
    opencode_url: str = "http://localhost:4096"
    mcp_http_port: int = 51364
    spawn_opencode: bool = True
    llm_temperature: float | None = None
    llm_top_p: float | None = None
    llm_top_k: int | None = None
    llm_min_p: float | None = None
    llm_presence_penalty: float | None = None
    llm_repetition_penalty: float | None = None
    ollama_url: str = "http://localhost:11434"
    vector_search_url: str = "http://localhost:51362"
    selected_model: str = ""
    agents_note_path: str = "AGENTS.md"

    env_vars: dict[str, str] = {}

    auto_allow_edit: bool = True
    auto_allow_create: bool = True
    auto_allow_delete: bool = False


def re_export_settings(settings: Settings) -> None:
    """Export settings back to environment variables for subprocesses."""
    for k, v in settings.env_vars.items():
        os.environ[k] = str(v)


_settings: list[Settings] = []


def get_settings() -> Settings:
    if not _settings:
        s = Settings()
        re_export_settings(s)
        logger.info(
            "settings loaded backend=%s model=%s mcp_port=%d opencode_url=%s env_vars=%d",
            s.llm_backend,
            s.llm_model,
            s.mcp_http_port,
            s.opencode_url,
            len(s.env_vars),
        )
        _settings.append(s)
    return _settings[0]


def invalidate_settings() -> None:
    logger.info("settings cache invalidated")
    _settings.clear()
