from __future__ import annotations

import asyncio
import collections.abc
import contextlib
import logging
import time
import typing
import uuid

import httpx
from opencode_ai import NOT_GIVEN, AsyncOpencode

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
_OPENCODE_TURN_DEADLINE_SECONDS = 240.0
_OPENCODE_STREAM_IDLE_GRACE_SECONDS = 1.0


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


async def _load_existing_message_ids(
    client: AsyncOpencode,
    session_id: str,
) -> set[str]:
    ids: set[str] = set()
    try:
        messages = await client.session.messages(session_id)
    except Exception:
        logger.debug(
            "opencode could not load baseline messages session=%s",
            session_id,
            exc_info=True,
        )
        return ids

    for message in messages:
        info = getattr(message, "info", None)
        msg_id = getattr(info, "id", None)
        if isinstance(msg_id, str) and msg_id:
            ids.add(msg_id)
    return ids


def _extract_session_error(event: object) -> str | None:
    props = getattr(event, "properties", None)
    if props is None:
        return None

    error = getattr(props, "error", None)
    if error is None:
        return None

    message = getattr(error, "message", None)
    if isinstance(message, str) and message:
        return message
    return str(error)


def _raise_turn_timeout() -> typing.NoReturn:
    raise TimeoutError


async def _post_message(  # noqa: PLR0913, PLR0917
    http_client: httpx.AsyncClient,
    session_id: str,
    user_message: str,
    model_id: str,
    provider_id: str,
    system_prompt: str | None,
    agent: str | None,
    message_id: str,
) -> httpx.Response:
    parts: list[typing.Any] = [{"text": user_message, "type": "text"}]
    body = {
        "parts": parts,
        "model": {
            "modelID": model_id,
            "providerID": provider_id,
        },
        "messageID": message_id,
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

    return await http_client.post(
        f"/session/{session_id}/message",
        json=body,
        headers={"Accept": "application/json", "User-Agent": "curl/8.7.1"},
        timeout=timeout,
    )


async def run_opencode_turn(  # noqa: PLR0912, PLR0913, PLR0914, PLR0915
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
    post_task: asyncio.Task[httpx.Response] | None = None
    logger.info(
        "opencode turn start session=%s provider=%s model=%s agent=%s message_len=%d",
        session_id,
        provider_id,
        model_id,
        agent or "dragonglass",
        len(user_message),
    )

    async with (
        httpx.AsyncClient(base_url=settings.opencode_url) as http_client,
        AsyncOpencode(base_url=settings.opencode_url) as opencode_client,
    ):
        try:
            existing_message_ids = await _load_existing_message_ids(
                opencode_client,
                session_id,
            )
            stream = await opencode_client.event.list()
            stream_iter = aiter(stream)

            user_message_id = str(uuid.uuid4())
            existing_message_ids.add(user_message_id)

            post_task = asyncio.create_task(
                _post_message(
                    http_client,
                    session_id,
                    user_message,
                    model_id,
                    provider_id,
                    system_prompt,
                    agent,
                    user_message_id,
                )
            )
            # Track the last seen text for each part ID to calculate deltas
            part_text_map: dict[str, str] = {}
            stream_idle_at: float | None = None
            streamed_text = False
            streamed_usage = False
            session_error: str | None = None

            async def _process_stream_event(  # noqa: PLR0911, PLR0912, PLR0914
                ev: typing.Any,
            ) -> collections.abc.AsyncGenerator[AgentEvent, None]:
                nonlocal streamed_text, streamed_usage, session_error, stream_idle_at

                await asyncio.sleep(0)  # satisfy RUF029 (async def without await)

                ev_type = getattr(ev, "type", "")
                props = getattr(ev, "properties", None)
                if props is None:
                    return

                if ev_type == "session.error":
                    session_error = _extract_session_error(ev)
                    return

                if ev_type == "session.idle":
                    idle_sid = getattr(props, "session_id", None)
                    if not idle_sid or idle_sid == session_id:
                        stream_idle_at = time.monotonic()
                    return

                if ev_type != "message.part.updated":
                    return

                # message.part.updated can contain either 'part' (full replacement)
                # or 'diff' (incremental update).
                part = getattr(props, "part", None)
                diff = getattr(props, "diff", None)

                if part is None and diff is None:
                    return

                # If we have both, 'part' is the source of truth for the ID and session.
                # If we only have 'diff', it should still have these fields according to docs.
                p_obj = part if part is not None else diff

                p_sid = getattr(p_obj, "session_id", None)
                if isinstance(p_sid, str) and p_sid != session_id:
                    return

                m_id = getattr(p_obj, "message_id", None)
                if isinstance(m_id, str) and m_id in existing_message_ids:
                    return

                p_id = getattr(p_obj, "id", None)
                if not isinstance(p_id, str) or not p_id:
                    return

                p_type = getattr(p_obj, "type", "")

                # Handle text updates
                if p_type in {"text", "thought", "reasoning"}:
                    new_text: str = ""

                    if diff is not None:
                        # If it's a diff, the text field is the delta
                        new_text = getattr(diff, "text", "")
                    elif part is not None:
                        # If it's a full part, calculate the delta
                        full_content = getattr(part, "text", "")
                        last_content = part_text_map.get(p_id, "")
                        if len(full_content) > len(last_content):
                            new_text = full_content[len(last_content) :]
                            part_text_map[p_id] = full_content
                        else:
                            new_text = ""

                    if new_text:
                        streamed_text = True
                        if p_type == "text":
                            yield TextChunk(text=new_text)
                        else:
                            # Show thoughts/reasoning as status updates to keep UI alive
                            yield StatusEvent(
                                message=f"Thinking: {new_text.strip()[:50]}..."
                            )

                elif p_type == "step-finish":
                    tokens = getattr(p_obj, "tokens", None)
                    if tokens is not None:
                        streamed_usage = True
                        p_tokens = int(getattr(tokens, "input", 0) or 0)
                        c_tokens = int(getattr(tokens, "output", 0) or 0)
                        t_tokens = p_tokens + c_tokens
                        yield UsageEvent(
                            prompt_tokens=p_tokens,
                            completion_tokens=c_tokens,
                            total_tokens=t_tokens,
                            session_total=t_tokens,
                        )

            while True:
                if time.monotonic() - turn_started >= _OPENCODE_TURN_DEADLINE_SECONDS:
                    _raise_turn_timeout()

                if post_task.done() and stream_idle_at is None:
                    post_task.result()
                    stream_idle_at = (
                        time.monotonic() + _OPENCODE_STREAM_IDLE_GRACE_SECONDS
                    )

                if stream_idle_at is not None and time.monotonic() >= stream_idle_at:
                    break

                try:
                    event = await asyncio.wait_for(anext(stream_iter), timeout=0.2)
                    async for chunk in _process_stream_event(event):
                        yield chunk
                    if session_error:
                        break
                except TimeoutError:
                    continue
                except StopAsyncIteration:
                    break

            remaining = _OPENCODE_TURN_DEADLINE_SECONDS - (
                time.monotonic() - turn_started
            )
            if remaining <= 0:
                _raise_turn_timeout()
            if post_task.done():
                raw_response = post_task.result()
            else:
                raw_response = await asyncio.wait_for(post_task, timeout=remaining)
            if stream_idle_at is None:
                stream_idle_at = time.monotonic() + _OPENCODE_STREAM_IDLE_GRACE_SECONDS

            while time.monotonic() < stream_idle_at:
                if time.monotonic() - turn_started >= _OPENCODE_TURN_DEADLINE_SECONDS:
                    _raise_turn_timeout()
                try:
                    event = await asyncio.wait_for(anext(stream_iter), timeout=0.2)
                    async for chunk in _process_stream_event(event):
                        yield chunk
                    if session_error:
                        break
                except TimeoutError:
                    continue
                except StopAsyncIteration:
                    break

            elapsed = time.monotonic() - turn_started
            logger.info(
                "opencode POST complete session=%s status=%d elapsed=%.2fs",
                session_id,
                raw_response.status_code,
                elapsed,
            )

            if session_error:
                logger.error(
                    "OpenCode session error session=%s error=%s",
                    session_id,
                    session_error,
                )
                yield StatusEvent(message=f"OpenCode Error: {session_error}")
                yield DoneEvent()
                return

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
            if tokens and not streamed_usage:
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
            if not streamed_text and not parts_list:
                await _log_session_state(
                    http_client, session_id, "opencode empty-response"
                )
                yield StatusEvent(
                    message=(
                        "OpenCode returned no response text for this turn. Try again."
                    )
                )

            if parts_list and not streamed_text:
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

        except TimeoutError:
            elapsed = time.monotonic() - turn_started
            logger.warning(
                "opencode hard timeout session=%s provider=%s model=%s elapsed=%.2fs deadline=%.1fs",
                session_id,
                provider_id,
                model_id,
                elapsed,
                _OPENCODE_TURN_DEADLINE_SECONDS,
                exc_info=True,
            )
            await _log_session_state(http_client, session_id, "opencode hard-timeout")
            yield StatusEvent(
                message=(
                    "OpenCode did not finish the turn in time. "
                    "Try again or simplify the request."
                )
            )
            yield DoneEvent()
            return

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
        except httpx.TransportError as exc:
            logger.warning(
                "opencode transport error session=%s provider=%s model=%s error=%s",
                session_id,
                provider_id,
                model_id,
                exc,
                exc_info=True,
            )
            await _log_session_state(
                http_client, session_id, "opencode transport-error"
            )
            yield StatusEvent(
                message=(
                    "OpenCode connection failed while sending or receiving this turn. "
                    "Try again."
                )
            )
            yield DoneEvent()
            return
        except asyncio.CancelledError:
            logger.info("opencode turn cancelled session=%s", session_id)
            raise

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
        finally:
            if post_task is None:
                pass
            elif not post_task.done():
                post_task.cancel()
                with contextlib.suppress(Exception):
                    await post_task
            else:
                with contextlib.suppress(Exception):
                    post_task.result()
