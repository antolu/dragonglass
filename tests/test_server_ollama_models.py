from __future__ import annotations

from dragonglass.server.server import format_ollama_chat_model_name


def test_format_ollama_chat_model_name_prefixes_bare_tag() -> None:
    assert format_ollama_chat_model_name("qwen3.5:35b") == "ollama_chat/qwen3.5:35b"


def test_format_ollama_chat_model_name_preserves_existing_provider() -> None:
    assert (
        format_ollama_chat_model_name("ollama_chat/qwen3.5:35b")
        == "ollama_chat/qwen3.5:35b"
    )


def test_format_ollama_chat_model_name_trims_whitespace() -> None:
    assert format_ollama_chat_model_name("  qwen3.5:35b  ") == "ollama_chat/qwen3.5:35b"
