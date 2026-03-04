from __future__ import annotations

import datetime
import logging
import pathlib

import httpx

from dragonglass.config import Settings

logger = logging.getLogger(__name__)

_PROMPT_PATH = pathlib.Path(__file__).parent / "system_prompt.md"


def _metadata_block() -> str:
    now = datetime.datetime.now()
    return (
        f"## Current context\n"
        f"- Today: {now.strftime('%A, %Y-%m-%d')}\n"
        f"- Time: {now.strftime('%H:%M')}\n"
    )


async def load_system_prompt(settings: Settings) -> tuple[str, bool]:
    vault_instructions, found = await _load_agents_note(settings)

    if _PROMPT_PATH.exists():
        global_instructions = _PROMPT_PATH.read_text(encoding="utf-8")
    else:
        logger.error("system prompt file not found at %s", _PROMPT_PATH)
        global_instructions = "You are a helpful assistant."

    prompt = global_instructions + "\n" + _metadata_block()
    if vault_instructions:
        prompt += "\n" + vault_instructions
    return prompt, found


async def _load_agents_note(settings: Settings) -> tuple[str, bool]:
    try:
        async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
            headers = {
                "Authorization": f"Bearer {settings.obsidian_api_key}",
                "Accept": "text/markdown",
            }
            resp = await client.get(
                f"{settings.obsidian_api_url}/vault/{settings.agents_note_path}",
                headers=headers,
            )
            if resp.status_code != httpx.codes.OK:
                return "", False
            return resp.text, True
    except Exception:
        logger.warning("failed to load agents note from vault", exc_info=True)
    return "", False
