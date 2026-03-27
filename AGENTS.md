# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# dragonglass — agent instructions

## Project overview

dragonglass is an LLM-powered Obsidian vault agent. A Python WebSocket server (`dragonglass/server/`) acts as the backend, with a Textual TUI (`dragonglass/tui/`) and a Swift/SwiftUI macOS app (`DragonglassApp/`) as frontends. External MCP servers are spawned at runtime via `npx`/`uvx`.

Python ≥ 3.11 is required. Everything is wired through `pyproject.toml`.

---

## Architecture

### Components

- **`dragonglass/agent/`** — `VaultAgent` runs the multi-turn LLM loop (max 20 iterations). It holds message history, dispatches tool calls, and emits typed `AgentEvent` objects as an async generator.
- **`dragonglass/server/`** — `DragonglassServer` is a WebSocket + HTTP server (default port 51363). It owns the `VaultAgent` instance, serialises `AgentEvent` objects to JSON, and handles commands from clients.
- **`dragonglass/mcp/`** — An HTTP/SSE MCP server (port 51364) exposing search and other tools. Also manages stdio MCP processes (`mcp-server-fetch` via `uvx`).
- **`dragonglass/search/`** — Search session backed by the Obsidian Vector Search plugin (separate HTTP server on port 51362).
- **`dragonglass/tui/`** — Textual TUI client; uses `AgentClient` (Python WebSocket) to talk to the server.
- **`DragonglassApp/`** — Swift/SwiftUI macOS app. `BackendManager` manages the Python venv lifecycle; `AgentClient.swift` owns the WebSocket connection.
- **`obsidian-plugin/`** — TypeScript Obsidian plugin providing the vector search HTTP server.

### WebSocket protocol

Clients send JSON commands; the server streams back newline-delimited JSON events.

**Inbound commands:** `chat`, `stop`, `ping`, `get_config`, `set_config`, `list_models`, `save_model`, `new_chat`, `list_conversations`, `load_conversation`, `delete_conversation`, `get_version`.

**Outbound events** (the `AgentEvent` union): `StatusEvent`, `TextChunk`, `ToolErrorEvent`, `UsageEvent`, `DoneEvent`, `FileAccessEvent`, `MCPToolEvent`, `ConversationsListEvent`, `ConversationLoadedEvent`, `UserMessageEvent`.

### Agent loop

```
chat command → VaultAgent.run(text)
  → _agent_loop: LLM call (litellm or OpenCode HTTP)
    → parse text + tool_calls
    → _call_tool: search tools → local; others → stdio MCP session
    → append tool result to history (truncated at 4000 chars)
  → loop until no tool_calls or max iterations
  → save conversation JSON → yield DoneEvent
```

### LLM backends

- **litellm** (default) — direct async completions; temperature/top-p/top-k from settings.
- **opencode** — external Node.js process spawned on startup; dragonglass writes its config, health-checks it, then proxies messages via HTTP. Falls back to litellm if startup fails.

Backend is selected by `llm_backend` in settings (`"litellm"` or `"opencode"`).

### Config & persistence

- **Settings:** `~/.config/dragonglass/config.toml` — loaded via Pydantic `BaseSettings`; singleton invalidated and reloaded on `set_config`.
- **Conversations:** `~/.cache/dragonglass/data/conversations/{uuid}.json` — auto-saved after each turn.
- **Extra models:** `~/.config/dragonglass/extra_models.json`.

---

## Commands

### Install

```bash
pip install -e ".[dev]"
pre-commit install
```

### Run tests

```bash
pytest                          # all tests
pytest tests/test_config_env_export.py          # single file
pytest tests/test_config_env_export.py::test_name  # single test
```

### Lint / format

```bash
pre-commit run --all-files
```

This runs (in order): ruff check with `--fix --unsafe-fixes --preview`, ruff format, mypy, and several pre-commit-hooks (trailing whitespace, TOML/YAML validation, JSON autoformat, etc.).

Do NOT run `ruff` or `mypy` standalone — use `pre-commit run --all-files` instead.

### Build

No explicit build step. The package is installed in editable mode. Version is derived from git tags via `setuptools-scm`.

---

## Code style

### Python version and future imports

Every Python file must start with:

```python
from __future__ import annotations
```

Target version is Python 3.11. Use Python 3.10+ syntax freely: `match`/`case`, `tomllib`, `|` union types, lowercase generic aliases (`list[str]`, `dict[str, int]`).

### Imports

**Standard library** — `import xxx` or `import xxx.yyy`, used as `xxx.Yyy` or `xxx.yyy.Zzz`:

```python
import asyncio
import collections.abc
import dataclasses
import json
import logging
import pathlib
import typing
```

**Third-party** — prefer bare `import pkg` and use qualified names. Use `from pkg import Cls` only when the symbol appears many times and the origin is obvious:

```python
import litellm
import httpx
import websockets

from pydantic_settings import BaseSettings, SettingsConfigDict
from textual.app import App, ComposeResult
```

**Intra-package** — always use `from dragonglass.xxx import Yyy`:

```python
from dragonglass.config import Settings, get_settings
from dragonglass.agent.agent import VaultAgent, AgentEvent
from dragonglass.log import setup_logging
```

No wildcard imports. All imports at the top of the file.

### Type hints

- All functions must have fully annotated signatures, including `-> None`.
- Use `|` for unions: `str | None`, `float | None`.
- Use lowercase generics: `list[str]`, `dict[str, Any]`, not `List`/`Dict`.
- Reference `typing.Any`, `typing.Literal`, `typing.ClassVar`, `typing.cast` via `import typing` then `typing.Xxx`.
- Use `collections.abc.AsyncGenerator` (not `typing.AsyncGenerator`) for async generator return types.
- Use `@dataclasses.dataclass` for event/message structs.
- Use `typing.TypedDict` for structured dicts (e.g. LLM message shapes).
- Define union type aliases at module level when reused: `AgentEvent = StatusEvent | TextChunk | ...`.

### Naming

| Kind | Convention | Example |
|------|-----------|---------|
| Classes | PascalCase | `VaultAgent`, `DragonglassServer` |
| Functions / methods | snake_case | `get_settings`, `setup_logging` |
| Module-level private | leading `_` | `_settings`, `_TOOL_STATUS` |
| Constants | SCREAMING_SNAKE_CASE | `DEFAULT_PORT`, `LOG_FILE` |
| Private class methods | leading `_` | `_agent_loop`, `_call_tool` |

### Error handling

- In background / server code, catch broad `Exception` and log with `logger.exception(...)` or `logger.warning(..., exc_info=True)`. Do not re-raise unless the caller must handle it.
- Catch specific exceptions only when the type matters: `FileNotFoundError`, `json.JSONDecodeError`, `websockets.exceptions.ConnectionClosed`.
- No custom exception classes.
- API-facing tool functions may return `{"error": "..."}` dicts instead of raising.
- Use `noqa` comments sparingly and only when the suppression is intentional (e.g. `# noqa: PLR0912` on a legitimately complex dispatch function).

### Logging

```python
logger = logging.getLogger(__name__)
```

at module level. Use `logger.debug`, `.info`, `.warning`, `.exception`. Never use `print` in production code.

### Docstrings

Minimal. Plain single-line strings only when the purpose is non-obvious. No NumPy / Google style. No `:param:` / `:returns:` sections. Tool functions registered with `@m.tool()` must have docstrings — these are sent to the LLM.

### General patterns

- f-strings throughout. No `.format()` or `%` formatting.
- `match`/`case` for dispatching over event/message types.
- Singleton state stored as a module-level list: `_cache: list[T] = []`, populated on first call.
- `frozenset({...})` for immutable name sets.
- `dict.fromkeys(iterable)` to deduplicate while preserving order.
- `@staticmethod` for methods that don't use `self`.
- No blank lines with trailing whitespace (enforced by pre-commit).

### What not to do

- Do not add comments unless the logic is genuinely opaque.
- Do not add `print` statements.
- Do not plan for backward compatibility unless explicitly asked.
- Do not name files or functions `xxx_new`, `xxx_refactor`, `xxx_unified`. Replace the existing file.
- Do not create summary or documentation markdown files unless explicitly asked.
- Do not use formal/cliché language ("comprehensive", "enhanced", "key features") in docstrings or docs.

---

## Tests

Tests live in `tests/`. Use functional test functions (`def test_something`), not class-based tests.

Async tests are called via `asyncio.run(...)` inside a sync test function — no `pytest-asyncio` marker needed.

Use `pytest.MonkeyPatch` (via the `monkeypatch` fixture) for environment and attribute patching.

```python
from __future__ import annotations

def test_something(monkeypatch: pytest.MonkeyPatch) -> None:
    ...
```

All tests must pass before finalising a commit. Run:

```bash
pre-commit run --all-files && pytest
```

---

## Git

- Conventional commits: `feat:`, `fix:`, `refactor:`, `chore:`, `test:`, `docs:`.
- Keep commit messages short — mention only what changed.
- Never commit with `--no-verify` unless explicitly instructed.
- Never use `git add -A`.
- Do not commit automatically — only when the user explicitly asks.
