from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import pathlib
import shutil
import signal
import subprocess
import time
import tomllib
import typing
import urllib.parse
from http import HTTPStatus

import httpx
import tomli_w

from dragonglass import paths
from dragonglass.agent.types import JsonValue
from dragonglass.config import LLMBackend, Settings, get_settings, invalidate_settings
from dragonglass.paths import OPENCODE_CONFIG_FILE

logger = logging.getLogger(__name__)

PROCESS_TERMINATE_TIMEOUT_SECONDS = 8.0
PROCESS_TERMINATE_GRACE_SECONDS = 0.4

OPENCODE_READY_TIMEOUT_SECONDS = 15.0
OPENCODE_READY_POLL_INTERVAL_SECONDS = 0.1
OPENCODE_HEALTHCHECK_TIMEOUT_SECONDS = 0.5
OPENCODE_HEALTHCHECK_STABILIZE_SECONDS = 0.35

DEFAULT_OPENCODE_PORT = 4096

_OPENCODE_PATH_PREFIX = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

_OPENCODE_CONFIG_TEMPLATE: dict[str, JsonValue] = {
    "$schema": "https://opencode.ai/config.json",
    "mcp": {
        "dragonglass": {
            "type": "remote",
            "enabled": True,
        }
    },
    "agent": {
        "dragonglass": {
            "mode": "primary",
            "tools": {
                "dragonglass_*": True,
            },
        }
    },
}


def _coerce_json_map(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, JsonValue] = {
        key: item for key, item in value.items() if isinstance(key, str)
    }
    return result


class OpenCodeManager:
    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None
        self._log_tasks: list[asyncio.Task[None]] = []
        self._last_model: str | None = None
        self.start_error: str | None = None

    @staticmethod
    def is_active(settings: Settings) -> bool:
        return settings.llm_backend == LLMBackend.opencode and settings.spawn_opencode

    @staticmethod
    def get_port(opencode_url: str) -> int:
        port = DEFAULT_OPENCODE_PORT
        try:
            parsed = urllib.parse.urlparse(opencode_url)
            if parsed.port:
                port = parsed.port
        except Exception:
            logger.warning("opencode: failed to parse OpenCode URL %s", opencode_url)
        return port

    @staticmethod
    def resolve_executable() -> str | None:
        explicit = os.environ.get("OPENCODE_BIN", "").strip()
        if explicit:
            expanded = os.path.expanduser(explicit)
            if os.path.isfile(expanded) and os.access(expanded, os.X_OK):
                return expanded
        discovered = shutil.which("opencode")
        if discovered:
            return discovered
        return None

    @staticmethod
    def list_listener_pids(port: int) -> list[int]:
        try:
            result = subprocess.run(
                ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                capture_output=True,
                text=True,
                check=False,
            )
            pids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            return [int(pid) for pid in pids if pid.isdigit()]
        except Exception:
            logger.warning(
                "opencode: failed listing listeners on port %d", port, exc_info=True
            )
            return []

    @staticmethod
    def pid_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        else:
            return True

    @staticmethod
    def _load_json_file(path: pathlib.Path) -> dict[str, JsonValue]:
        try:
            with open(path, encoding="utf-8") as f:
                loaded = json.load(f)
            data = _coerce_json_map(loaded)
            if data:
                logger.info("opencode: loaded config source %s", path)
                return data
            if loaded != {}:
                logger.warning("opencode: ignoring non-object config file %s", path)
        except FileNotFoundError:
            return {}
        except Exception:
            logger.warning(
                "opencode: failed reading config file %s", path, exc_info=True
            )
        return {}

    @staticmethod
    def _merge_config_dicts(
        base: dict[str, JsonValue], incoming: dict[str, JsonValue]
    ) -> dict[str, JsonValue]:
        for key, value in incoming.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                existing = _coerce_json_map(base[key])
                merged_child = OpenCodeManager._merge_config_dicts(
                    existing,
                    _coerce_json_map(value),
                )
                base[key] = merged_child
            else:
                base[key] = value
        return base

    def _build_config(self, model_id: str) -> dict[str, JsonValue]:
        settings = get_settings()
        merged: dict[str, JsonValue] = self._merge_config_dicts(
            {},
            _OPENCODE_CONFIG_TEMPLATE,
        )

        local_config = self._load_json_file(OPENCODE_CONFIG_FILE)
        if local_config:
            merged = self._merge_config_dicts(merged, local_config)

        mcp = _coerce_json_map(merged.setdefault("mcp", {}))
        merged["mcp"] = mcp
        mcp_config = _coerce_json_map(mcp.setdefault("dragonglass", {}))
        mcp["dragonglass"] = mcp_config
        mcp_config["type"] = "remote"
        mcp_config["url"] = settings.mcp_service_url(path="/mcp")
        mcp_config["enabled"] = True

        agent = _coerce_json_map(merged.setdefault("agent", {}))
        merged["agent"] = agent
        agent_config = _coerce_json_map(agent.setdefault("dragonglass", {}))
        agent["dragonglass"] = agent_config
        agent_config["mode"] = "primary"
        agent_tools = _coerce_json_map(agent_config.setdefault("tools", {}))
        agent_config["tools"] = agent_tools
        agent_tools["dragonglass_*"] = True
        if model_id.strip():
            agent_config["model"] = model_id

        return merged

    def write_config(self, model_id: str) -> None:
        OPENCODE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        config = self._build_config(model_id)
        with open(OPENCODE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.info(
            "opencode: wrote config to %s (model=%s)",
            OPENCODE_CONFIG_FILE,
            model_id,
        )

    async def stop(self) -> None:
        if self._process and self._process.returncode is None:
            logger.info(
                "opencode: terminating server (pid %d)",
                self._process.pid,
            )
            self._process.terminate()
            try:
                await asyncio.wait_for(
                    self._process.wait(),
                    timeout=PROCESS_TERMINATE_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                logger.warning(
                    "opencode: process did not terminate in time; killing pid %d",
                    self._process.pid,
                )
                self._process.kill()
                await self._process.wait()
        self._process = None
        self._last_model = None
        for task in self._log_tasks:
            task.cancel()
        if self._log_tasks:
            await asyncio.gather(*self._log_tasks, return_exceptions=True)
        self._log_tasks = []

    async def kill_stale_on_port(self, port: int) -> None:
        for pid in self.list_listener_pids(port):
            if self._process and pid == self._process.pid:
                continue

            try:
                proc = subprocess.run(
                    ["ps", "-o", "command=", "-p", str(pid)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                command = proc.stdout.strip().lower()
            except Exception:
                logger.warning(
                    "opencode: failed reading process command for pid %d",
                    pid,
                    exc_info=True,
                )
                continue

            if "opencode" not in command:
                continue

            logger.warning(
                "opencode: killing stale process pid=%d on port %d", pid, port
            )
            with contextlib.suppress(Exception):
                os.kill(pid, signal.SIGTERM)

            await asyncio.sleep(PROCESS_TERMINATE_GRACE_SECONDS)
            if self.pid_exists(pid):
                logger.warning("opencode: forcing stale process pid=%d to stop", pid)
                with contextlib.suppress(Exception):
                    os.kill(pid, signal.SIGKILL)

    async def _wait_for_server(self, opencode_url: str) -> None:
        deadline = time.monotonic() + OPENCODE_READY_TIMEOUT_SECONDS
        last_error: Exception | None = None
        url = opencode_url.rstrip("/") + "/"

        while time.monotonic() < deadline:
            if self._process and self._process.returncode is not None:
                raise RuntimeError(
                    f"OpenCode process exited early with code {self._process.returncode}"
                )
            try:
                async with httpx.AsyncClient(
                    timeout=OPENCODE_HEALTHCHECK_TIMEOUT_SECONDS
                ) as client:
                    resp = await client.get(url)
                    if resp.status_code < HTTPStatus.INTERNAL_SERVER_ERROR:
                        await asyncio.sleep(OPENCODE_HEALTHCHECK_STABILIZE_SECONDS)
                        if self._process and self._process.returncode is not None:
                            raise RuntimeError(  # noqa: TRY301
                                f"OpenCode process exited after health check with code {self._process.returncode}"
                            )
                        logger.info(
                            "opencode: health check status=%d url=%s",
                            resp.status_code,
                            url,
                        )
                        return
            except Exception as exc:
                last_error = exc

            await asyncio.sleep(OPENCODE_READY_POLL_INTERVAL_SECONDS)

        raise RuntimeError(
            f"Timed out waiting for OpenCode at {opencode_url}"
        ) from last_error

    async def fallback_to_litellm(self, reason: str) -> None:
        self.start_error = reason
        await self.stop()

        current = _read_config_toml()
        changed = False
        if current.get("llm_backend") == LLMBackend.opencode:
            current["llm_backend"] = LLMBackend.litellm
            changed = True

        if changed:
            _write_config_toml(current)
            invalidate_settings()
            logger.warning(
                "opencode: switched llm_backend to litellm because OpenCode is unavailable"
            )

    async def restart(self, model_id: str) -> bool:
        """Kills existing OpenCode server and restarts."""
        settings = get_settings()
        if not settings.spawn_opencode:
            self.start_error = None
            return True

        await self.stop()
        await self.kill_stale_on_port(self.get_port(settings.opencode_url))

        executable = self.resolve_executable()
        if not executable:
            self.start_error = (
                "OpenCode binary not found. Install opencode-ai or set OPENCODE_BIN."
            )
            logger.error("opencode: %s", self.start_error)
            await self.fallback_to_litellm(self.start_error)
            return False

        try:
            self.write_config(model_id)
        except Exception:
            logger.warning("opencode: failed to update config", exc_info=True)

        port = self.get_port(settings.opencode_url)

        try:
            env = os.environ.copy()
            env["OPENCODE_CONFIG"] = str(OPENCODE_CONFIG_FILE)
            env["PATH"] = _OPENCODE_PATH_PREFIX + ":" + env.get("PATH", "")
            logger.info(
                "opencode: launching process exe=%s port=%d config=%s",
                executable,
                port,
                OPENCODE_CONFIG_FILE,
            )
            self._process = await asyncio.create_subprocess_exec(
                executable,
                "serve",
                "--port",
                str(port),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            async def log_stream(stream: asyncio.StreamReader) -> None:
                try:
                    while True:
                        line = await stream.readline()
                        if not line:
                            break
                        logger.info("[opencode] %s", line.decode("utf-8").rstrip())
                except Exception:
                    logger.debug("opencode: log stream closed", exc_info=True)

            if self._process.stdout:
                self._log_tasks.append(
                    asyncio.create_task(log_stream(self._process.stdout))
                )
            if self._process.stderr:
                self._log_tasks.append(
                    asyncio.create_task(log_stream(self._process.stderr))
                )
            await self._wait_for_server(settings.opencode_url)
            logger.info(
                "opencode: server started with model %s (pid %d)",
                model_id,
                self._process.pid,
            )
            self.start_error = None
            self._last_model = model_id
        except Exception:
            logger.exception("opencode: failed to restart")
            self.start_error = "Failed to start OpenCode server. Check OPENCODE_BIN and npm installation."
            await self.fallback_to_litellm(self.start_error)
            return False

        return True

    @property
    def last_model(self) -> str | None:
        return self._last_model


def _read_config_toml() -> dict[str, JsonValue]:
    try:
        with open(paths.CONFIG_FILE, "rb") as f:
            loaded = tomllib.load(f)
        return _coerce_json_map(typing.cast(JsonValue, loaded))
    except FileNotFoundError:
        return {}


def _write_config_toml(data: dict[str, JsonValue]) -> None:
    paths.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(paths.CONFIG_FILE, "wb") as f:
        tomli_w.dump(data, f)
