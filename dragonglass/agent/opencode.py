from __future__ import annotations

import collections.abc
import logging
import time
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

_OPENCODE_MESSAGE_TIMEOUT_SECONDS = 180.0


def _preview_text(value: object, limit: int = 500) -> str:
    if value is None:
        return ""
    text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [truncated {len(text) - limit} chars]"


def _summarize_parts(parts: list[typing.Any]) -> str:
    counts: dict[str, int] = {}
    for part in parts:
        part_type = "unknown"
        if isinstance(part, dict):
            raw_type = part.get("type")
            if isinstance(raw_type, str) and raw_type:
                part_type = raw_type
        counts[part_type] = counts.get(part_type, 0) + 1
    return ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))


async def _log_session_state(
    http_client: httpx.AsyncClient,
    session_id: str,
    prefix: str,
) -> None:
    try:
        session_resp = await http_client.get(
            f"/session/{session_id}",
            timeout=15.0,
        )
        logger.warning(
            "%s session fetch status=%d body=%s",
            prefix,
            session_resp.status_code,
            _preview_text(session_resp.text, 1000),
        )
    except Exception:
        logger.warning("%s failed to fetch session state", prefix, exc_info=True)


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
    turn_started = time.monotonic()
    logger.info(
        "opencode turn start session=%s provider=%s model=%s agent=%s message_len=%d",
        session_id,
        provider_id,
        model_id,
        agent or "dragonglass",
        len(user_message),
    )

    async with httpx.AsyncClient(base_url=settings.opencode_url) as http_client:
        try:
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

            timeout = httpx.Timeout(_OPENCODE_MESSAGE_TIMEOUT_SECONDS, connect=10.0)
            logger.debug(
                "opencode POST /session/%s/message timeout=%.1fs body=%s",
                session_id,
                _OPENCODE_MESSAGE_TIMEOUT_SECONDS,
                _preview_text(body, 400),
            )
            raw_response = await http_client.post(
                f"/session/{session_id}/message",
                json=body,
                headers={"Accept": "application/json", "User-Agent": "curl/8.7.1"},
                timeout=timeout,
            )

            elapsed = time.monotonic() - turn_started
            logger.info(
                "opencode POST complete session=%s status=%d elapsed=%.2fs",
                session_id,
                raw_response.status_code,
                elapsed,
            )

            if raw_response.status_code != 200:  # noqa: PLR2004
                logger.error(
                    "OpenCode returned status=%d body=%s",
                    raw_response.status_code,
                    _preview_text(raw_response.text, 2000),
                )
                await _log_session_state(http_client, session_id, "opencode non-200")
                yield DoneEvent()
                return

            data: dict[str, typing.Any] = raw_response.json()
            logger.debug("opencode response body=%s", _preview_text(data, 2000))

            info: dict[str, typing.Any] = data.get("info", {})
            tokens = info.get("tokens", {})
            if tokens:
                yield UsageEvent(
                    prompt_tokens=int(tokens.get("input", 0)),
                    completion_tokens=int(tokens.get("output", 0)),
                    total_tokens=int(tokens.get("total", 0)),
                    session_total=int(tokens.get("total", 0)),  # simplified
                )
                logger.info(
                    "opencode usage session=%s input=%s output=%s total=%s",
                    session_id,
                    tokens.get("input", 0),
                    tokens.get("output", 0),
                    tokens.get("total", 0),
                )

            parts_list = data.get("parts", [])
            if not isinstance(parts_list, list):
                logger.warning(
                    "opencode response parts is not a list: %s",
                    type(parts_list).__name__,
                )
                parts_list = []

            logger.info(
                "opencode response parts session=%s count=%d summary=%s",
                session_id,
                len(parts_list),
                _summarize_parts(parts_list) if parts_list else "none",
            )
            if parts_list:
                for part in parts_list:
                    if part.get("type") == "text":
                        text = part.get("text", "")
                        logger.debug(
                            "opencode text part session=%s chars=%d preview=%s",
                            session_id,
                            len(text),
                            _preview_text(text, 300),
                        )
                        yield TextChunk(text=text)
                    elif part.get("type") == "tool":
                        logger.info(
                            "opencode tool part session=%s payload=%s",
                            session_id,
                            _preview_text(part, 500),
                        )

            logger.info(
                "opencode turn done session=%s elapsed=%.2fs",
                session_id,
                time.monotonic() - turn_started,
            )

            yield DoneEvent()

        except httpx.ReadTimeout:
            elapsed = time.monotonic() - turn_started
            logger.warning(
                "opencode read timeout session=%s provider=%s model=%s elapsed=%.2fs timeout=%.1fs",
                session_id,
                provider_id,
                model_id,
                elapsed,
                _OPENCODE_MESSAGE_TIMEOUT_SECONDS,
                exc_info=True,
            )
            await _log_session_state(http_client, session_id, "opencode timeout")
            yield StatusEvent(
                message=(
                    "OpenCode timed out while processing the turn. "
                    "Try again or simplify the request."
                )
            )
            yield DoneEvent()
            return

        except Exception as exc:
            logger.exception(
                "OpenCode turn failed session=%s provider=%s model=%s",
                session_id,
                provider_id,
                model_id,
            )
            await _log_session_state(http_client, session_id, "opencode exception")
            yield StatusEvent(message=f"OpenCode Error: {exc}")
            yield DoneEvent()
