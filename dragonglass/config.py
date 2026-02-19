from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    obsidian_api_url: str = "http://localhost:27123"
    obsidian_api_key: str = ""
    ollama_url: str = "http://localhost:11434"
    vector_search_url: str = "http://localhost:51362"
    llm_model: str = "gemini/gemini-2.5-flash"
    agents_note_path: str = "AGENTS.md"


_settings: list[Settings] = []


def get_settings() -> Settings:
    if not _settings:
        _settings.append(Settings())
    return _settings[0]
