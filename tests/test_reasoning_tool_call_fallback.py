from __future__ import annotations

from dragonglass.agent import parse_tool_calls_from_text


def test_parses_single_tool_call() -> None:
    text = (
        "I need to search for levente.\n\n"
        "<tool_call>\n"
        "<function=keyword_search>\n"
        "<parameter=queries>\n"
        '["levente", "tag:#type/people"]\n'
        "</parameter>\n"
        "</function>\n"
        "</tool_call>"
    )
    result = parse_tool_calls_from_text(text)
    assert result == [("keyword_search", {"queries": ["levente", "tag:#type/people"]})]


def test_parses_multiple_tool_calls() -> None:
    text = (
        "<tool_call>\n"
        "<function=new_search_session>\n"
        "</function>\n"
        "</tool_call>\n"
        "<tool_call>\n"
        "<function=keyword_search>\n"
        '<parameter=queries>["foo"]</parameter>\n'
        "</function>\n"
        "</tool_call>"
    )
    result = parse_tool_calls_from_text(text)
    assert result == [
        ("new_search_session", {}),
        ("keyword_search", {"queries": ["foo"]}),
    ]


def test_returns_empty_when_no_tool_calls() -> None:
    assert parse_tool_calls_from_text("just thinking, no tool call here") == []


def test_returns_empty_on_empty_string() -> None:
    assert parse_tool_calls_from_text("") == []


def test_string_parameter_fallback_when_not_valid_json() -> None:
    text = (
        "<tool_call>\n"
        "<function=open_note>\n"
        "<parameter=path>some/path/note.md</parameter>\n"
        "</function>\n"
        "</tool_call>"
    )
    result = parse_tool_calls_from_text(text)
    assert result == [("open_note", {"path": "some/path/note.md"})]


def test_parses_no_parameters() -> None:
    text = "<tool_call>\n<function=new_search_session>\n</function>\n</tool_call>"
    result = parse_tool_calls_from_text(text)
    assert result == [("new_search_session", {})]
