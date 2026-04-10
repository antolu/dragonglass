from __future__ import annotations

import logging
import typing

import httpx

from dragonglass.config import Settings
from dragonglass.mcp.edit.frontmatter import (
    ManageFrontmatterArgs,
    PatchLinesArgs,
    _get_frontmatter_key_value,
    _strip_tag_prefix,
    delete_frontmatter_key_lines,
    rebuild_note_with_frontmatter,
    set_frontmatter_key_lines,
    split_frontmatter_block,
)
from dragonglass.search.session import get_current_session, new_session

logger = logging.getLogger(__name__)

_NOTE_ERROR_MESSAGES: dict[str, str] = {
    "note_not_found": "Note not found in vault. The file may have been deleted or the path is wrong.",
    "invalid_path": "Path must end with .md.",
    "invalid_body": "Malformed request body.",
}

_PATCH_ERROR_MESSAGES: dict[str, str] = {
    "note_not_found": "Note not found in vault. The file may have been deleted or the path is wrong.",
    "hash_mismatch": "Note was modified since it was last read. Call read_note_with_hash again before patching.",
    "line_range_out_of_bounds": "Line range exceeds the number of lines in the note.",
    "invalid_line_range": "Invalid line range: start_line must be >= 1 and <= end_line.",
}


def _coerce_json_map(value: typing.Any) -> dict[str, typing.Any]:
    if not isinstance(value, dict):
        return {}
    return {key: item for key, item in value.items() if isinstance(key, str)}


def _parse_response_json(resp: httpx.Response) -> dict[str, typing.Any] | None:
    try:
        result = typing.cast(typing.Any, resp.json())
        if isinstance(result, dict):
            return _coerce_json_map(result)
    except Exception:
        pass
    return None


async def do_read_note_with_hash(  # noqa: PLR0911
    settings: Settings,
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> dict[str, typing.Any]:
    logger.info(
        "read_note_with_hash start path=%s range=%s-%s",
        path,
        start_line,
        end_line,
    )
    session = get_current_session()
    if not session:
        return {
            "error": "No active search session. Call dragonglass_new_search_session first."
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.vector_search_url}/notes/read",
                params={"path": path},
            )
            if resp.status_code == httpx.codes.OK:
                data = _parse_response_json(resp)
                if data is None:
                    return {"error": "Vector search server returned empty response."}
                content_hash = data.get("content_hash")
                if isinstance(content_hash, str):
                    session.set_last_read_hash(path, content_hash)

                content_raw = data.get("content", "")
                content = (
                    content_raw if isinstance(content_raw, str) else str(content_raw)
                )
                lines = content.splitlines()
                total_lines = len(lines)

                # Format content with line numbers
                # We use L{n}: format to be clear for the LLM
                formatted_lines = [f"L{i + 1}: {line}" for i, line in enumerate(lines)]

                if start_line is not None or end_line is not None:
                    s = (start_line if start_line is not None else 1) - 1
                    e = end_line if end_line is not None else total_lines
                    # Clamp values
                    s = max(0, min(s, total_lines))
                    e = max(s, min(e, total_lines))
                    display_lines = formatted_lines[s:e]
                else:
                    display_lines = formatted_lines

                data["content_with_line_numbers"] = "\n".join(display_lines)
                data["total_lines"] = total_lines
                logger.info(
                    "read_note_with_hash done path=%s total_lines=%d selected_lines=%d",
                    path,
                    total_lines,
                    len(display_lines),
                )
                return data

            data = _parse_response_json(resp)
            error_value = data.get("error", "") if data else ""
            error_code = error_value if isinstance(error_value, str) else ""
            message = _NOTE_ERROR_MESSAGES.get(error_code)
            if message:
                return {"error": message}
            if data:
                return {"error": f"HTTP {resp.status_code}", "details": data}
            return {
                "error": (
                    f"Vector search server returned HTTP {resp.status_code} with no body. "
                    "The Obsidian plugin may not be running or may need to be reloaded."
                )
            }
    except httpx.ConnectError:
        logger.warning(
            "read_note_with_hash connect error path=%s vector_search_url=%s",
            path,
            settings.vector_search_url,
        )
        return {
            "error": (
                f"Cannot connect to vector search server at {settings.vector_search_url}. "
                "The Obsidian plugin is likely not running."
            )
        }
    except Exception as exc:
        logger.exception("read_note_with_hash failed for path %r", path)
        return {"error": str(exc)}


async def do_patch_note_lines(  # noqa: PLR0911
    settings: Settings,
    args: PatchLinesArgs,
) -> dict[str, typing.Any]:
    session = get_current_session() or new_session()

    path = args["path"]
    resolved_expected_hash = args["expected_hash"] or session.get_last_read_hash(path)
    if not resolved_expected_hash:
        return {
            "error": (
                "No stored hash for this file. Call dragonglass_read_note_with_hash(path) before "
                "calling any note edit tool."
            )
        }

    payload = {
        "path": path,
        "start_line": args["start_line"],
        "end_line": args["end_line"],
        "replacement": args["replacement"],
        "expected_hash": resolved_expected_hash,
    }
    logger.info(
        "patch_note_lines start path=%s start_line=%d end_line=%d replacement_chars=%d",
        path,
        args["start_line"],
        args["end_line"],
        len(args["replacement"]),
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(
                f"{settings.vector_search_url}/notes/patch-lines",
                json=payload,
            )
            if resp.status_code == httpx.codes.OK:
                data = _parse_response_json(resp)
                if data is None:
                    return {"error": "Vector search server returned empty response."}
                new_hash = data.get("new_hash")
                if isinstance(new_hash, str):
                    session.set_last_read_hash(path, new_hash)
                logger.info(
                    "patch_note_lines done path=%s new_hash=%s",
                    path,
                    bool(data.get("new_hash")),
                )
                return data

            data = _parse_response_json(resp)
            error_value = data.get("error", "") if data else ""
            error_code = error_value if isinstance(error_value, str) else ""
            message = _PATCH_ERROR_MESSAGES.get(error_code)
            if message:
                return {"error": message}
            if data:
                return {"error": f"HTTP {resp.status_code}", "details": data}
            return {
                "error": (
                    f"Vector search server returned HTTP {resp.status_code} with no body. "
                    "The Obsidian plugin may not be running or may need to be reloaded."
                )
            }
    except httpx.ConnectError:
        logger.warning(
            "patch_note_lines connect error path=%s vector_search_url=%s",
            path,
            settings.vector_search_url,
        )
        return {
            "error": (
                f"Cannot connect to vector search server at {settings.vector_search_url}. "
                "The Obsidian plugin is likely not running."
            )
        }
    except Exception as exc:
        logger.exception("patch_note_lines failed for path %r", path)
        return {"error": str(exc)}


async def patch_entire_note(
    settings: Settings,
    path: str,
    expected_hash: str,
    original_content: str,
    new_content: str,
) -> dict[str, typing.Any]:
    total_lines = len(original_content.splitlines())
    end_line = total_lines if total_lines > 0 else 1
    return await do_patch_note_lines(
        settings,
        {
            "path": path,
            "start_line": 1,
            "end_line": end_line,
            "replacement": new_content,
            "expected_hash": expected_hash,
        },
    )


async def do_manage_frontmatter(  # noqa: PLR0911
    settings: Settings,
    args: ManageFrontmatterArgs,
) -> dict[str, typing.Any]:
    path = args["path"]
    operation = args["operation"]
    key = args["key"].strip()
    logger.info(
        "manage_frontmatter start path=%s operation=%s key=%s",
        path,
        operation,
        key,
    )
    if not key:
        return {"error": "key is required"}

    read_result = await do_read_note_with_hash(settings, path)
    if "error" in read_result:
        return read_result

    content = str(read_result.get("content", ""))
    content_hash = read_result.get("content_hash")
    if not isinstance(content_hash, str) or not content_hash:
        return {"error": "Note read did not return content_hash"}

    frontmatter_lines, rest, had_frontmatter = split_frontmatter_block(content)

    if operation == "get":
        value, exists = _get_frontmatter_key_value(frontmatter_lines, key)
        logger.info(
            "manage_frontmatter done path=%s operation=%s key=%s exists=%s",
            path,
            operation,
            key,
            exists,
        )
        return {
            "path": path,
            "operation": operation,
            "key": key,
            "value": value,
            "exists": exists,
        }

    if operation == "set":
        if "value" not in args:
            return {"error": "value is required for set operation"}
        value = args["value"]
        if key == "tags" and isinstance(value, list):
            value = [
                _strip_tag_prefix(str(tag))
                for tag in value
                if _strip_tag_prefix(str(tag))
            ]
        updated_frontmatter_lines = set_frontmatter_key_lines(
            frontmatter_lines,
            key,
            value,
        )
        new_content = rebuild_note_with_frontmatter(
            updated_frontmatter_lines,
            rest,
            had_frontmatter,
        )
        patch_result = await patch_entire_note(
            settings, path, content_hash, content, new_content
        )
        if "error" in patch_result:
            logger.warning(
                "manage_frontmatter failed path=%s operation=%s key=%s error=%s",
                path,
                operation,
                key,
                patch_result.get("error"),
            )
            return patch_result
        logger.info(
            "manage_frontmatter done path=%s operation=%s key=%s",
            path,
            operation,
            key,
        )
        return {
            "path": path,
            "operation": operation,
            "key": key,
            "value": value,
        }

    if operation == "delete":
        updated_frontmatter_lines, deleted = delete_frontmatter_key_lines(
            frontmatter_lines,
            key,
        )
        if not deleted:
            logger.info(
                "manage_frontmatter done path=%s operation=%s key=%s deleted=false",
                path,
                operation,
                key,
            )
            return {
                "path": path,
                "operation": operation,
                "key": key,
                "deleted": False,
            }
        new_content = rebuild_note_with_frontmatter(
            updated_frontmatter_lines,
            rest,
            had_frontmatter,
        )
        patch_result = await patch_entire_note(
            settings, path, content_hash, content, new_content
        )
        if "error" in patch_result:
            logger.warning(
                "manage_frontmatter failed path=%s operation=%s key=%s error=%s",
                path,
                operation,
                key,
                patch_result.get("error"),
            )
            return patch_result
        logger.info(
            "manage_frontmatter done path=%s operation=%s key=%s deleted=true",
            path,
            operation,
            key,
        )
        return {
            "path": path,
            "operation": operation,
            "key": key,
            "deleted": True,
        }

    return {"error": f"Invalid operation: {operation}"}
