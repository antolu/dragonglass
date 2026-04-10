from __future__ import annotations

import json
import re
import typing

from pydantic import JsonValue


class PatchLinesArgs(typing.TypedDict):
    path: str
    start_line: int
    end_line: int
    replacement: str
    expected_hash: str | None


class ManageFrontmatterArgs(typing.TypedDict):
    path: str
    operation: typing.Literal["get", "set", "delete"]
    key: str
    value: typing.NotRequired[JsonValue]


class ManageTagsArgs(typing.TypedDict):
    path: str
    operation: typing.Literal["add", "remove", "list"]
    tags: typing.NotRequired[list[str]]


_MIN_QUOTED_STRING_LEN = 2


def _parse_scalar(value: str) -> JsonValue:  # noqa: PLR0911
    stripped = value.strip()
    if stripped == "true":
        return True
    if stripped == "false":
        return False
    if stripped == "null":
        return None
    if re.fullmatch(r"-?\d+", stripped):
        try:
            return int(stripped)
        except ValueError:
            return stripped
    if re.fullmatch(r"-?\d+\.\d+", stripped):
        try:
            return float(stripped)
        except ValueError:
            return stripped
    if (
        (stripped.startswith('"') and stripped.endswith('"'))
        or (stripped.startswith("'") and stripped.endswith("'"))
    ) and len(stripped) >= _MIN_QUOTED_STRING_LEN:
        return stripped[1:-1]
    if stripped.startswith("[") and stripped.endswith("]"):
        inner = stripped[1:-1].strip()
        if not inner:
            return []
        parts = [part.strip() for part in inner.split(",")]
        result: list[JsonValue] = []
        for part in parts:
            parsed = _parse_scalar(part)
            parsed_str = str(parsed).lstrip("#")
            if parsed_str.strip():
                result.append(parsed_str)
        return result
    return stripped


def _yaml_scalar(value: JsonValue) -> str:  # noqa: PLR0911
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        if not value:
            return '""'
        if re.search(r"[:\[\]{}#,\n\r\t]|^\s|\s$", value):
            escaped = value.replace('"', '\\"')
            return f'"{escaped}"'
        return value
    return json.dumps(value, ensure_ascii=True)


def _strip_tag_prefix(tag: str) -> str:
    cleaned = tag.strip()
    if cleaned.startswith("#"):
        return cleaned[1:]
    return cleaned


_FRONTMATTER_BLOCK_RE = re.compile(r"\A---\n(?P<fm>[\s\S]*?)\n---(?P<rest>[\s\S]*)\Z")
_FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)\s*:(.*)$")


def _split_frontmatter_block(content: str) -> tuple[list[str], str, bool]:
    match = _FRONTMATTER_BLOCK_RE.match(content)
    if not match:
        return [], content, False
    frontmatter_text = match.group("fm")
    rest = match.group("rest")
    frontmatter_lines = frontmatter_text.split("\n") if frontmatter_text else []
    return frontmatter_lines, rest, True


def _rebuild_note_with_frontmatter(  # noqa: PLR0911
    frontmatter_lines: list[str],
    rest: str,
    had_frontmatter: bool,
) -> str:
    if not frontmatter_lines:
        if not had_frontmatter:
            return rest
        if rest.startswith("\n"):
            return rest[1:]
        return rest

    fm = "\n".join(frontmatter_lines)
    if had_frontmatter:
        return f"---\n{fm}\n---{rest}"
    if not rest:
        return f"---\n{fm}\n---\n"
    if rest.startswith("\n"):
        return f"---\n{fm}\n---{rest}"
    return f"---\n{fm}\n---\n\n{rest}"


def _body_from_frontmatter_rest(rest: str) -> str:
    if rest.startswith("\n"):
        return rest[1:]
    return rest


def _find_frontmatter_key_span(
    frontmatter_lines: list[str],
    key: str,
) -> tuple[int, int] | None:
    for i, line in enumerate(frontmatter_lines):
        match = _FRONTMATTER_KEY_RE.match(line)
        if not match:
            continue
        if match.group(1).strip() != key:
            continue
        j = i + 1
        while j < len(frontmatter_lines):
            if _FRONTMATTER_KEY_RE.match(frontmatter_lines[j]):
                break
            j += 1
        return i, j
    return None


def _parse_frontmatter_value_from_span(span_lines: list[str]) -> JsonValue:
    if not span_lines:
        return None
    match = _FRONTMATTER_KEY_RE.match(span_lines[0])
    if not match:
        return None
    inline_value = match.group(2).strip()
    if inline_value:
        return _parse_scalar(inline_value)

    list_items: list[JsonValue] = []
    for line in span_lines[1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lstripped = line.lstrip()
        if lstripped.startswith("- "):
            list_items.append(_parse_scalar(lstripped[2:].strip()))
            continue
        return "\n".join(span_lines[1:]).strip()
    if list_items:
        return list_items
    return None


def _serialize_frontmatter_entry(key: str, value: JsonValue) -> list[str]:
    if isinstance(value, list):
        if not value:
            return [f"{key}: []"]
        lines = [f"{key}:"]
        lines.extend(f"  - {_yaml_scalar(item)}" for item in value)
        return lines
    return [f"{key}: {_yaml_scalar(value)}"]


def _set_frontmatter_key_lines(
    frontmatter_lines: list[str],
    key: str,
    value: JsonValue,
) -> list[str]:
    replacement = _serialize_frontmatter_entry(key, value)
    span = _find_frontmatter_key_span(frontmatter_lines, key)
    if span is None:
        return frontmatter_lines + replacement
    start, end = span
    return frontmatter_lines[:start] + replacement + frontmatter_lines[end:]


def _delete_frontmatter_key_lines(
    frontmatter_lines: list[str],
    key: str,
) -> tuple[list[str], bool]:
    span = _find_frontmatter_key_span(frontmatter_lines, key)
    if span is None:
        return frontmatter_lines, False
    start, end = span
    updated = frontmatter_lines[:start] + frontmatter_lines[end:]
    while updated and not updated[0].strip():
        updated = updated[1:]
    while updated and not updated[-1].strip():
        updated = updated[:-1]
    return updated, True


def _collect_inline_tags(body: str) -> list[str]:
    tags = re.findall(r"(?<![\w/#])#([A-Za-z0-9_\-/]+)", body)
    return list(dict.fromkeys(tag for tag in tags if tag))


def _remove_inline_tags(body: str, tags_to_remove: set[str]) -> str:
    updated = body
    for tag in tags_to_remove:
        rx = re.compile(rf"(^|[^\w#-])#{re.escape(tag)}\b", re.MULTILINE)
        updated = rx.sub(r"\1", updated)
    updated = re.sub(r"[ \t]+\n", "\n", updated)
    return re.sub(r"\n{3,}", "\n\n", updated)


def _get_frontmatter_key_value(
    frontmatter_lines: list[str],
    key: str,
) -> tuple[JsonValue, bool]:
    span = _find_frontmatter_key_span(frontmatter_lines, key)
    if span is None:
        return None, False
    start, end = span
    value = _parse_frontmatter_value_from_span(frontmatter_lines[start:end])
    return value, True
