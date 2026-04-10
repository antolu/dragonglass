from __future__ import annotations

from dragonglass._mod_replace import replace_modname
from dragonglass.mcp.search.frontmatter import (
    ManageFrontmatterArgs,
    ManageTagsArgs,
    PatchLinesArgs,
    delete_frontmatter_key_lines,
    rebuild_note_with_frontmatter,
    remove_inline_tags,
    set_frontmatter_key_lines,
    split_frontmatter_block,
)
from dragonglass.mcp.search.notes import (
    do_manage_frontmatter,
    do_patch_note_lines,
    do_read_note_with_hash,
)
from dragonglass.mcp.search.tags import do_manage_tags
from dragonglass.mcp.search.tools import create_search_server

for _sym in (  # noqa: RUF067
    create_search_server,
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
    "create_search_server",
    "delete_frontmatter_key_lines",
    "do_manage_frontmatter",
    "do_manage_tags",
    "do_patch_note_lines",
    "do_read_note_with_hash",
    "rebuild_note_with_frontmatter",
    "remove_inline_tags",
    "set_frontmatter_key_lines",
    "split_frontmatter_block",
]
