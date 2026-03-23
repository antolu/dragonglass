from __future__ import annotations

import collections.abc
import logging
import typing

import httpx
from opencode_ai import NOT_GIVEN

from dragonglass.agent.types import (
    AgentEvent,
    DoneEvent,
    StatusEvent,
    TextChunk,
    UsageEvent,
)
from dragonglass.config import Settings

logger = logging.getLogger(__name__)


async def run_opencode_turn(  # noqa: PLR0913
    session_id: str,
    user_message: str,
    model_id: str,
    provider_id: str,
    settings: Settings,
    *,
    system_prompt: str | None = None,
    agent: str | None = None,
) -> collections.abc.AsyncGenerator[AgentEvent]:
    # We use httpx directly because the SDK's parsing of chunked responses
    # produced empty bodies in this environment.
    async with httpx.AsyncClient(base_url=settings.opencode_url) as http_client:
        try:
            # OpenCode requires parts for prompt.
            parts: list[typing.Any] = [{"text": user_message, "type": "text"}]

            body = {
                "parts": parts,
                "model": {
                    "modelID": model_id,
                    "providerID": provider_id,
                },
                "agent": agent or "dragonglass",
                "system": system_prompt if system_prompt is not None else NOT_GIVEN,
            }

            raw_response = await http_client.post(
                f"/session/{session_id}/message",
                json=body,
                headers={"Accept": "application/json", "User-Agent": "curl/8.7.1"},
                timeout=60.0,
            )

            if raw_response.status_code != 200:  # noqa: PLR2004
                logger.error(
                    "OpenCode returned %d: %s",
                    raw_response.status_code,
                    raw_response.text,
                )
                yield DoneEvent()
                return

            data: dict[str, typing.Any] = raw_response.json()

            logger.debug("--- RECEIVED FROM OPENCODE (HTTPX) ---")
            logger.debug(data)

            # Extract usage info
            info: dict[str, typing.Any] = data.get("info", {})
            tokens = info.get("tokens", {})
            if tokens:
                yield UsageEvent(
                    prompt_tokens=int(tokens.get("input", 0)),
                    completion_tokens=int(tokens.get("output", 0)),
                    total_tokens=int(tokens.get("total", 0)),
                    session_total=int(tokens.get("total", 0)),  # simplified
                )

            # The response structure is {"info": {...}, "parts": [...]}
            parts_list = data.get("parts", [])
            if parts_list:
                for part in parts_list:
                    if part.get("type") == "text":
                        text = part.get("text", "")
                        yield TextChunk(text=text)
                    elif part.get("type") == "tool":
                        logger.debug("Tool call in parts: %s", part)

            yield DoneEvent()

        except Exception as exc:
            logger.exception("OpenCode turn failed")
            yield StatusEvent(message=f"OpenCode Error: {exc}")
            yield DoneEvent()
