from __future__ import annotations

import enum
import logging

from pydantic import JsonValue

from dragonglass.config import Settings

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


__all__ = ["DragonglassTool", "needs_approval"]
