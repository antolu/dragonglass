from __future__ import annotations

import datetime
import logging

import httpx

from dragonglass.config import Settings

logger = logging.getLogger(__name__)

_GLOBAL_INSTRUCTIONS = """\
You are a personal knowledge management assistant for an Obsidian vault.

Core rules you must always follow:
- Never invent or assume facts. Only record what the user explicitly states.
- If you cannot find the requested information in the vault after reasonable search attempts, state "I don't know" rather than guessing.
- Use the same language as the note you are editing or creating.
- Prefer updating existing notes over creating new ones.
- Before modifying a note, always read it first to understand existing content.
- For surgical edits (adding a fact, updating a line), use obsidian_search_replace.
- For new notes or complete rewrites, use obsidian_update_note.
- Be concise when updating notes — match the style of existing content.

## Searching the vault

Before answering any question or making any change, you should explore the vault. You have several tools at your disposal:

1. **keyword_search**: Use this to find candidate files using specific queries.
    - You MUST initialize a new session with `new_search_session` before starting keyword or vector searches.
    - Use prefixes for precision: `file:`, `tag:#tag`, `section:`, `property:`.
    - **CRITICAL**: For `tag:` searches, you MUST only use tags that appear in the custom vault instructions below (if any). Do not guess tags.
2. **vector_search**: Use this for natural language semantic ranking.
    - If you already ran `keyword_search`, `vector_search` will rank those results.
    - If you didn't find specific candidates with keywords, you can use `vector_search` to search the entire vault.
3. **obsidian_read_note**: Always read promising notes to confirm relevance before acting.

If you find yourself retrying the same search parameters without new results, stop and inform the user you couldn't find the information.
"""


def _metadata_block() -> str:
    now = datetime.datetime.now()
    return (
        f"## Current context\n"
        f"- Today: {now.strftime('%A, %Y-%m-%d')}\n"
        f"- Time: {now.strftime('%H:%M')}\n"
    )


async def load_system_prompt(settings: Settings) -> tuple[str, bool]:
    vault_instructions, found = await _load_agents_note(settings)
    prompt = _GLOBAL_INSTRUCTIONS + "\n" + _metadata_block()
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
