from __future__ import annotations

import difflib
import enum
import logging
import typing

import httpx
from pydantic import JsonValue

from dragonglass.config import Settings
from dragonglass.mcp.search.frontmatter import (
    _delete_frontmatter_key_lines,
    _rebuild_note_with_frontmatter,
    _remove_inline_tags,
    _set_frontmatter_key_lines,
    _split_frontmatter_block,
)

logger = logging.getLogger(__name__)


class DragonglassTool(enum.StrEnum):
    REPLACE_LINES = "dragonglass_replace_lines"
    INSERT_AFTER_LINE = "dragonglass_insert_after_line"
    DELETE_LINES = "dragonglass_delete_lines"
    MANAGE_FRONTMATTER = "dragonglass_manage_frontmatter"
    MANAGE_TAGS = "dragonglass_manage_tags"
    NEW_SEARCH_SESSION = "dragonglass_new_search_session"
    KEYWORD_SEARCH = "dragonglass_keyword_search"
    VECTOR_SEARCH = "dragonglass_vector_search"
    RUN_COMMAND = "dragonglass_run_command"
    READ_NOTE_WITH_HASH = "dragonglass_read_note_with_hash"
    OPEN_NOTE = "dragonglass_open_note"


_TOOL_PERMISSIONS: dict[str, str] = {
    DragonglassTool.REPLACE_LINES: "edit",
    DragonglassTool.INSERT_AFTER_LINE: "edit",
    DragonglassTool.DELETE_LINES: "delete",
    DragonglassTool.MANAGE_FRONTMATTER: "edit",
    DragonglassTool.MANAGE_TAGS: "edit",
}


def needs_approval(  # noqa: PLR0911
    tool_name: str,
    args: dict[str, JsonValue],
    settings: Settings,
    session_approved: set[str],
) -> str | None:
    perm = _TOOL_PERMISSIONS.get(tool_name)
    if perm is None:
        return None
    if (
        tool_name == DragonglassTool.MANAGE_FRONTMATTER
        and args.get("operation") == "get"
    ):
        return None
    if tool_name == DragonglassTool.MANAGE_TAGS and args.get("operation") == "list":
        return None
    if perm == "edit" and settings.auto_allow_edit:
        return None
    if perm == "delete" and settings.auto_allow_delete:
        return None
    if perm == "create" and settings.auto_allow_create:
        return None
    if perm in session_approved:
        return None
    return perm


async def compute_diff(  # noqa: PLR0912, PLR0914, PLR0915
    tool_name: str,
    args: dict[str, JsonValue],
    vector_search_url: str,
) -> tuple[str, str, str]:
    path = str(args.get("path", ""))
    if not path:
        return "", "", tool_name

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{vector_search_url}/notes/read",
                params={"path": path},
            )
        if resp.status_code != 200:  # noqa: PLR2004
            return path, "", f"{tool_name} on {path}"
        data = resp.json()
        original = str(data.get("content", ""))
    except Exception:
        logger.warning("approval gate: failed to fetch %r for diff", path)
        return path, "", f"{tool_name} on {path}"

    original_lines = original.splitlines(keepends=True)

    try:
        if tool_name == DragonglassTool.REPLACE_LINES:
            start = int(typing.cast(int, args.get("start_line", 1)))
            end = int(typing.cast(int, args.get("end_line", start)))
            replacement = str(args.get("replacement", ""))
            new_lines = list(original_lines)
            new_lines[start - 1 : end] = [
                ln if ln.endswith("\n") else ln + "\n"
                for ln in replacement.splitlines()
            ]
            description = f"Replace lines {start}-{end} in {path}"

        elif tool_name == DragonglassTool.INSERT_AFTER_LINE:
            line = int(typing.cast(int, args.get("line", 0)))
            text = str(args.get("text", ""))
            new_lines = list(original_lines)
            insert_lines = [
                ln if ln.endswith("\n") else ln + "\n" for ln in text.splitlines()
            ]
            new_lines[line:line] = insert_lines
            description = f"Insert after line {line} in {path}"

        elif tool_name == DragonglassTool.DELETE_LINES:
            start = int(typing.cast(int, args.get("start_line", 1)))
            end = int(typing.cast(int, args.get("end_line", start)))
            new_lines = list(original_lines)
            del new_lines[start - 1 : end]
            description = f"Delete lines {start}-{end} in {path}"

        elif tool_name == DragonglassTool.MANAGE_FRONTMATTER:
            op = str(args.get("operation", ""))
            key = str(args.get("key", ""))
            value = args.get("value")
            fm_lines, rest, had = _split_frontmatter_block(original)
            if op == "set":
                fm_lines = _set_frontmatter_key_lines(fm_lines, key, value)
            elif op == "delete":
                fm_lines, _ = _delete_frontmatter_key_lines(fm_lines, key)
            new_content = _rebuild_note_with_frontmatter(fm_lines, rest, had)
            new_lines = new_content.splitlines(keepends=True)
            description = f"Frontmatter {op} '{key}' in {path}"

        elif tool_name == DragonglassTool.MANAGE_TAGS:
            op = str(args.get("operation", ""))
            tags = args.get("tags", [])
            tags_list = tags if isinstance(tags, list) else []
            fm_lines, rest, had = _split_frontmatter_block(original)
            if op == "remove":
                body = rest.lstrip("\n")
                updated_body = _remove_inline_tags(body, {str(t) for t in tags_list})
                new_content = _rebuild_note_with_frontmatter(
                    fm_lines,
                    f"\n{updated_body}" if rest.startswith("\n") else updated_body,
                    had,
                )
                new_lines = new_content.splitlines(keepends=True)
            else:
                new_lines = original_lines
            description = f"Tags {op} {tags_list!r} in {path}"

        else:
            return path, "", f"{tool_name} on {path}"

    except Exception:
        logger.warning(
            "approval gate: diff computation failed for %r",
            tool_name,
            exc_info=True,
        )
        return path, "", f"{tool_name} on {path}"

    diff_lines = list(
        difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=3,
        )
    )
    return path, "".join(diff_lines), description
