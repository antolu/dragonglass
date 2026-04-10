from __future__ import annotations

from dragonglass._mod_replace import replace_modname
from dragonglass.mcp.edit.frontmatter import (
    ManageFrontmatterArgs,
    ManageTagsArgs,
    PatchLinesArgs,
)
from dragonglass.mcp.edit.notes import (
    do_manage_frontmatter,
    do_patch_note_lines,
    do_read_note_with_hash,
)
from dragonglass.mcp.edit.tags import do_manage_tags

for _sym in (  # noqa: RUF067
    do_manage_frontmatter,
    do_manage_tags,
    do_patch_note_lines,
    do_read_note_with_hash,
):
    replace_modname(_sym, __name__)

__all__ = [
    "ManageFrontmatterArgs",
    "ManageTagsArgs",
    "PatchLinesArgs",
    "do_manage_frontmatter",
    "do_manage_tags",
    "do_patch_note_lines",
    "do_read_note_with_hash",
]
