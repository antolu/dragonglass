from __future__ import annotations

import logging
import typing

from pydantic import JsonValue

from dragonglass.config import Settings
from dragonglass.mcp.search.frontmatter import (
    ManageTagsArgs,
    _body_from_frontmatter_rest,
    _collect_inline_tags,
    _get_frontmatter_key_value,
    _strip_tag_prefix,
    delete_frontmatter_key_lines,
    rebuild_note_with_frontmatter,
    remove_inline_tags,
    set_frontmatter_key_lines,
    split_frontmatter_block,
)
from dragonglass.mcp.search.notes import _patch_entire_note, do_read_note_with_hash

logger = logging.getLogger(__name__)


async def do_manage_tags(  # noqa: PLR0911, PLR0912, PLR0914
    settings: Settings,
    args: ManageTagsArgs,
) -> dict[str, JsonValue]:

    path = args["path"]
    operation = args["operation"]
    raw_tags = args.get("tags", [])
    normalized_tags = [
        _strip_tag_prefix(tag) for tag in raw_tags if _strip_tag_prefix(tag)
    ]
    logger.info(
        "manage_tags start path=%s operation=%s tags=%d",
        path,
        operation,
        len(normalized_tags),
    )

    read_result = await do_read_note_with_hash(settings, path)
    if "error" in read_result:
        return read_result

    content = str(read_result.get("content", ""))
    content_hash = read_result.get("content_hash")
    if not isinstance(content_hash, str) or not content_hash:
        return {"error": "Note read did not return content_hash"}

    frontmatter_lines, rest, had_frontmatter = split_frontmatter_block(content)
    body = _body_from_frontmatter_rest(rest)
    frontmatter_tags_raw, has_frontmatter_tags = _get_frontmatter_key_value(
        frontmatter_lines,
        "tags",
    )
    if not has_frontmatter_tags:
        frontmatter_tags_raw = []
    if isinstance(frontmatter_tags_raw, list):
        frontmatter_tags = [
            _strip_tag_prefix(str(tag))
            for tag in frontmatter_tags_raw
            if _strip_tag_prefix(str(tag))
        ]
    elif isinstance(frontmatter_tags_raw, str):
        frontmatter_tags = (
            [_strip_tag_prefix(frontmatter_tags_raw)]
            if _strip_tag_prefix(frontmatter_tags_raw)
            else []
        )
    else:
        frontmatter_tags = []
    inline_tags = _collect_inline_tags(body)
    current_tags = list(dict.fromkeys(frontmatter_tags + inline_tags))

    if operation == "list":
        logger.info(
            "manage_tags done path=%s operation=list total=%d", path, len(current_tags)
        )
        return {
            "path": path,
            "operation": operation,
            "tags": typing.cast(list[JsonValue], current_tags),
        }

    if not normalized_tags:
        return {"error": "tags is required for add/remove"}

    if operation == "add":
        merged = list(dict.fromkeys(frontmatter_tags + normalized_tags))
        updated_frontmatter_lines = set_frontmatter_key_lines(
            frontmatter_lines,
            "tags",
            typing.cast(list[JsonValue], merged),
        )
        new_content = rebuild_note_with_frontmatter(
            updated_frontmatter_lines,
            rest,
            had_frontmatter,
        )
        patch_result = await _patch_entire_note(
            settings,
            path,
            content_hash,
            content,
            new_content,
        )
        if "error" in patch_result:
            logger.warning(
                "manage_tags failed path=%s operation=add error=%s",
                path,
                patch_result.get("error"),
            )
            return patch_result
        logger.info(
            "manage_tags done path=%s operation=add added=%d total=%d",
            path,
            len([tag for tag in normalized_tags if tag not in frontmatter_tags]),
            len(merged),
        )
        return {
            "path": path,
            "operation": operation,
            "added": typing.cast(
                list[JsonValue],
                [tag for tag in normalized_tags if tag not in frontmatter_tags],
            ),
            "tags": typing.cast(list[JsonValue], merged),
        }

    if operation == "remove":
        to_remove = set(normalized_tags)
        updated_frontmatter_tags = [
            tag for tag in frontmatter_tags if tag not in to_remove
        ]
        updated_frontmatter_lines = frontmatter_lines
        if updated_frontmatter_tags:
            updated_frontmatter_lines = set_frontmatter_key_lines(
                updated_frontmatter_lines,
                "tags",
                typing.cast(list[JsonValue], updated_frontmatter_tags),
            )
        else:
            updated_frontmatter_lines, _ = delete_frontmatter_key_lines(
                updated_frontmatter_lines,
                "tags",
            )
        updated_body = remove_inline_tags(body, to_remove)
        updated_rest = f"\n{updated_body}" if rest.startswith("\n") else updated_body
        new_content = rebuild_note_with_frontmatter(
            updated_frontmatter_lines,
            updated_rest,
            had_frontmatter,
        )
        patch_result = await _patch_entire_note(
            settings,
            path,
            content_hash,
            content,
            new_content,
        )
        if "error" in patch_result:
            logger.warning(
                "manage_tags failed path=%s operation=remove error=%s",
                path,
                patch_result.get("error"),
            )
            return patch_result
        final_tags = list(
            dict.fromkeys(updated_frontmatter_tags + _collect_inline_tags(updated_body))
        )
        logger.info(
            "manage_tags done path=%s operation=remove removed=%d total=%d",
            path,
            len([tag for tag in normalized_tags if tag in current_tags]),
            len(final_tags),
        )
        return {
            "path": path,
            "operation": operation,
            "removed": typing.cast(
                list[JsonValue],
                [tag for tag in normalized_tags if tag in current_tags],
            ),
            "tags": typing.cast(list[JsonValue], final_tags),
        }

    return {"error": f"Invalid operation: {operation}"}
