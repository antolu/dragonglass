from __future__ import annotations

import os

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from dragonglass import paths


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

    obsidian_api_url: str = "http://localhost:27123"
    obsidian_api_key: str = ""
    llm_model: str = "ollama/llama3.2"
    llm_temperature: float | None = None
    llm_top_p: float | None = None
    llm_top_k: int | None = None
    llm_min_p: float | None = None
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
    for field_name, value in settings.model_dump().items():
        env_var = field_name.upper()
        if isinstance(value, bool):
            os.environ[env_var] = str(value).lower()
        elif isinstance(value, dict):
            for k, v in value.items():
                os.environ[k] = str(v)
        else:
            os.environ[env_var] = str(value)


_settings: list[Settings] = []


def get_settings() -> Settings:
    if not _settings:
        s = Settings()
        re_export_settings(s)
        _settings.append(s)
    return _settings[0]


def invalidate_settings() -> None:
    _settings.clear()
