from __future__ import annotations

import enum
import logging
import os
import socket
import urllib.parse

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

    @staticmethod
    def _format_http_host(host: str) -> str:
        return f"[{host}]" if ":" in host and not host.startswith("[") else host

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        return list(dict.fromkeys(items))

    def _resolve_hosts(self, base_url: str) -> list[str]:
        parsed = urllib.parse.urlparse(base_url)
        host = parsed.hostname
        if host is None:
            return []
        hosts = [host]
        try:
            infos = socket.getaddrinfo(host, parsed.port or 80, type=socket.SOCK_STREAM)
            for info in infos:
                addr = info[4][0]
                if isinstance(addr, str):
                    hosts.append(addr)
        except socket.gaierror:
            pass
        return self._dedupe(hosts)

    def build_http_url(self, host: str, port: int, path: str = "") -> str:
        normalized_path = path if path.startswith("/") else f"/{path}"
        if normalized_path == "/":
            normalized_path = ""
        return f"http://{self._format_http_host(host)}:{port}{normalized_path}"

    def mcp_probe_urls(self, port: int, path: str = "/mcp") -> list[str]:
        hosts = self._resolve_hosts(self.opencode_url)
        if not hosts:
            parsed = urllib.parse.urlparse(self.opencode_url)
            if parsed.hostname:
                hosts = [parsed.hostname]
        return [self.build_http_url(host, port, path) for host in hosts]

    def ollama_probe_urls(self) -> list[str]:
        parsed = urllib.parse.urlparse(self.ollama_url)
        port = parsed.port or 11434
        return [
            self.build_http_url(host, port)
            for host in self._resolve_hosts(self.ollama_url)
        ]

    def mcp_service_url(self, path: str = "/mcp") -> str:
        urls = self.mcp_probe_urls(self.mcp_http_port, path=path)
        if urls:
            return urls[0]
        parsed = urllib.parse.urlparse(self.opencode_url)
        host = parsed.hostname or socket.gethostname()
        return self.build_http_url(host, self.mcp_http_port, path)

    def bind_host(self) -> str:
        parsed = urllib.parse.urlparse(self.opencode_url)
        if parsed.hostname:
            return parsed.hostname
        return socket.gethostname()


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
