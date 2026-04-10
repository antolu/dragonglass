from __future__ import annotations

import difflib
import logging
import typing

import httpx
from pydantic import JsonValue

from dragonglass.mcp.edit.frontmatter import (
    delete_frontmatter_key_lines,
    rebuild_note_with_frontmatter,
    remove_inline_tags,
    set_frontmatter_key_lines,
    split_frontmatter_block,
)

logger = logging.getLogger(__name__)

_REPLACE_LINES = "dragonglass_replace_lines"
_INSERT_AFTER_LINE = "dragonglass_insert_after_line"
_DELETE_LINES = "dragonglass_delete_lines"
_MANAGE_FRONTMATTER = "dragonglass_manage_frontmatter"
_MANAGE_TAGS = "dragonglass_manage_tags"


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
        if tool_name == _REPLACE_LINES:
            start = int(typing.cast(int, args.get("start_line", 1)))
            end = int(typing.cast(int, args.get("end_line", start)))
            replacement = str(args.get("replacement", ""))
            new_lines = list(original_lines)
            new_lines[start - 1 : end] = [
                ln if ln.endswith("\n") else ln + "\n"
                for ln in replacement.splitlines()
            ]
            description = f"Replace lines {start}-{end} in {path}"

        elif tool_name == _INSERT_AFTER_LINE:
            line = int(typing.cast(int, args.get("line", 0)))
            text = str(args.get("text", ""))
            new_lines = list(original_lines)
            insert_lines = [
                ln if ln.endswith("\n") else ln + "\n" for ln in text.splitlines()
            ]
            new_lines[line:line] = insert_lines
            description = f"Insert after line {line} in {path}"

        elif tool_name == _DELETE_LINES:
            start = int(typing.cast(int, args.get("start_line", 1)))
            end = int(typing.cast(int, args.get("end_line", start)))
            new_lines = list(original_lines)
            del new_lines[start - 1 : end]
            description = f"Delete lines {start}-{end} in {path}"

        elif tool_name == _MANAGE_FRONTMATTER:
            op = str(args.get("operation", ""))
            key = str(args.get("key", ""))
            value = args.get("value")
            fm_lines, rest, had = split_frontmatter_block(original)
            if op == "set":
                fm_lines = set_frontmatter_key_lines(fm_lines, key, value)
            elif op == "delete":
                fm_lines, _ = delete_frontmatter_key_lines(fm_lines, key)
            new_content = rebuild_note_with_frontmatter(fm_lines, rest, had)
            new_lines = new_content.splitlines(keepends=True)
            description = f"Frontmatter {op} '{key}' in {path}"

        elif tool_name == _MANAGE_TAGS:
            op = str(args.get("operation", ""))
            tags = args.get("tags", [])
            tags_list = tags if isinstance(tags, list) else []
            fm_lines, rest, had = split_frontmatter_block(original)
            if op == "remove":
                body = rest.lstrip("\n")
                updated_body = remove_inline_tags(body, {str(t) for t in tags_list})
                new_content = rebuild_note_with_frontmatter(
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
