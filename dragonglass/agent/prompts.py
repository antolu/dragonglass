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

Before answering any question or making any change, search the vault. Follow this exact order:

**Step 1 — always call `new_search_session` first.** This is mandatory. `keyword_search` and `vector_search` will fail if you skip it.

**Step 2 — call `keyword_search`** with one or more query strings.
- Use prefixes for precision: `file:`, `tag:#tag`, `section:`, `property:`.
- **CRITICAL**: For `tag:` searches, only use tags that appear in the custom vault instructions below (if any). Do not guess tags.

**Step 3 — call `vector_search`** to semantically rank the keyword results, or to search the full vault if keywords returned nothing.

**Step 4 — call `obsidian_read_note`** on the most relevant files before answering or making changes.

If you find yourself retrying the same search without new results, stop and tell the user you couldn't find the information.
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
