from __future__ import annotations

import json
import re

from pydantic import JsonValue

_MAX_TOOL_RESULT_CHARS = 4000
_EVENT_TUPLE_LEN = 2


def _truncate_result(text: str) -> str:
    if len(text) <= _MAX_TOOL_RESULT_CHARS:
        return text
    return (
        text[:_MAX_TOOL_RESULT_CHARS]
        + f"\n[truncated — {len(text) - _MAX_TOOL_RESULT_CHARS} chars omitted]"
    )


def _is_validation_error_result(result: str) -> bool:
    return result.startswith("Tool '") and "called with wrong arguments" in result


def _is_error_result(result: str) -> bool:
    if _is_validation_error_result(result):
        return False
    if result.startswith(("Search server error:", "Tool '")):
        return True
    try:
        data = json.loads(result)
        return isinstance(data, dict) and "error" in data
    except json.JSONDecodeError:
        return False


def _fmt_args(args: dict[str, JsonValue]) -> str:
    return ", ".join(f"{k}={json.dumps(v)}" for k, v in args.items())


_RX_TOOL_CALL_BLOCK = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
_RX_TOOL_CALL_FN = re.compile(r"<function=([^>]+)>")
_RX_TOOL_CALL_PARAM = re.compile(r"<parameter=([^>]+)>(.*?)</parameter>", re.DOTALL)


def parse_tool_calls_from_text(
    text: str,
) -> list[tuple[str, dict[str, JsonValue]]]:
    """Parse Qwen3-style XML tool calls from free text.

    Handles the case where the model emits tool calls inside its <think> block
    (reasoning_content) rather than as structured tool_calls.
    """
    results: list[tuple[str, dict[str, JsonValue]]] = []
    for block in _RX_TOOL_CALL_BLOCK.findall(text):
        fn_match = _RX_TOOL_CALL_FN.search(block)
        if not fn_match:
            continue
        name = fn_match.group(1).strip()
        params: dict[str, JsonValue] = {}
        for pm in _RX_TOOL_CALL_PARAM.finditer(block):
            key = pm.group(1).strip()
            val_raw = pm.group(2).strip()
            try:
                params[key] = json.loads(val_raw)
            except json.JSONDecodeError:
                params[key] = val_raw
        results.append((name, params))
    return results


def _summarize_turn(
    tool_calls_made: list[tuple[str, dict[str, JsonValue], str]],
) -> str:
    if not tool_calls_made:
        return ""
    lines = []
    for name, args, result in tool_calls_made:
        preview = result[:120].replace("\n", " ").strip()
        lines.append(f"- {name}({_fmt_args(args)}) → {preview}")
    return "Actions taken:\n" + "\n".join(lines)
