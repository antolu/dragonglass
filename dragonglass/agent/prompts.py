from __future__ import annotations

import httpx

from dragonglass.config import Settings

_GLOBAL_INSTRUCTIONS = """\
You are a personal knowledge management assistant for an Obsidian vault.

Core rules you must always follow:
- Never invent or assume facts. Only record what the user explicitly states.
- Use the same language as the note you are editing or creating.
- Prefer updating existing notes over creating new ones.
- Before modifying a note, always read it first to understand existing content.
- For surgical edits (adding a fact, updating a line), use obsidian_search_replace.
- For new notes or complete rewrites, use obsidian_update_note.
- Always search the vault first to find relevant existing notes before creating new ones.
- Be concise when updating notes — match the style of existing content.
"""

_VAULT_PROMPT_FALLBACK = """\
## Vault Layout
- People notes: `02-Resources/People/` with tag `type/people`
- Area notes: `01-Areas/` with tag `type/area`
- Resource notes: `02-Resources/` with tag `type/resource`
- Daily notes: `00-System/Daily Notes/`
- Inbox (unsorted): `00-System/Inbox/`

## Note conventions
- Use YAML frontmatter with a `tags:` field
- People notes: filename = person's first name
"""


async def load_system_prompt(settings: Settings) -> str:
    vault_instructions = await _load_agents_note(settings)
    return _GLOBAL_INSTRUCTIONS + "\n" + vault_instructions


async def _load_agents_note(settings: Settings) -> str:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.obsidian_api_url}/vault/{settings.agents_note_path}",
                headers={
                    "Authorization": f"Bearer {settings.obsidian_api_key}",
                    "Accept": "text/markdown",
                },
                verify=False,
            )
            if resp.status_code == httpx.codes.OK:
                return resp.text
    except Exception:
        pass
    return _VAULT_PROMPT_FALLBACK
