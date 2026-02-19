from __future__ import annotations

import datetime
import re
import urllib.parse

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
- Be concise when updating notes — match the style of existing content.

## Searching the vault

Before answering any question or making any change, you must search the vault. Follow this process:

1. **Initialize search**: Call `new_search_session` to start a fresh search session.
2. **Structured keyword search**: Call `keyword_search` with one or more specific queries to narrow down candidate files. Use prefixes for precision:
   - `file:term` (filename matches)
   - `tag:#tag` (tag matches)
   - `section:term` (heading matches)
   - `property:term` (frontmatter key matches)
   Example: `keyword_search(queries=["file:Milano", "tag:#travel", "Milano Ancona"])`
3. **Semantic vector search**: Call `vector_search` with the user's natural language query. This will automatically use the results from `keyword_search` as an allowlist, ranking them by similarity. If `keyword_search` found nothing, it will search the entire vault.
4. **Read before acting**: Read promising notes with `obsidian_read_note` to confirm relevance.

Never give up after one failed search. If you find nothing, try broader keywords or different prefixes.
"""

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


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
            text = resp.text
            text = await _resolve_wikilinks(text, settings, client, headers)
            return text, True
    except Exception:
        pass
    return "", False


async def _resolve_wikilinks(
    text: str,
    settings: Settings,
    client: httpx.AsyncClient,
    headers: dict[str, str],
) -> str:
    links = _WIKILINK_RE.findall(text)
    if not links:
        return text

    vault_files = await _list_vault_files(settings, client, headers)

    for link_name in dict.fromkeys(links):
        path = _find_file(link_name.strip(), vault_files)
        if path is None:
            continue
        content = await _fetch_note(settings, client, headers, path)
        if content is None:
            continue
        text = re.sub(
            r"\[\[" + re.escape(link_name) + r"(?:[|#][^\]]*)?\]\]",
            f"\n---\n### {link_name}\n{content.strip()}\n---\n",
            text,
        )

    return text


async def _list_vault_files(
    settings: Settings,
    client: httpx.AsyncClient,
    headers: dict[str, str],
) -> list[str]:
    try:
        resp = await client.get(
            f"{settings.obsidian_api_url}/vault/",
            headers={**headers, "Accept": "application/json"},
        )
        if resp.status_code == httpx.codes.OK:
            data = resp.json()
            return data.get("files", [])
    except Exception:
        pass
    return []


def _find_file(name: str, files: list[str]) -> str | None:
    name_lower = name.lower()
    for path in files:
        basename = path.rsplit("/", 1)[-1]
        if basename.lower() in {name_lower, f"{name_lower}.md"}:
            return path
    return None


async def _fetch_note(
    settings: Settings,
    client: httpx.AsyncClient,
    headers: dict[str, str],
    path: str,
) -> str | None:
    try:
        encoded = urllib.parse.quote(path, safe="/")
        resp = await client.get(
            f"{settings.obsidian_api_url}/vault/{encoded}",
            headers=headers,
        )
        if resp.status_code == httpx.codes.OK:
            return resp.text
    except Exception:
        pass
    return None
