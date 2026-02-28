from __future__ import annotations

from dragonglass.server.server import (
    format_ollama_chat_model_name,
    is_embedding_model,
    parse_ollama_models,
)


def test_format_ollama_chat_model_name_prefixes_bare_tag() -> None:
    assert format_ollama_chat_model_name("qwen3.5:35b") == "ollama_chat/qwen3.5:35b"


def test_format_ollama_chat_model_name_preserves_existing_provider() -> None:
    assert (
        format_ollama_chat_model_name("ollama_chat/qwen3.5:35b")
        == "ollama_chat/qwen3.5:35b"
    )


def test_format_ollama_chat_model_name_trims_whitespace() -> None:
    assert format_ollama_chat_model_name("  qwen3.5:35b  ") == "ollama_chat/qwen3.5:35b"


def test_is_embedding_model_detects_embedding_tags() -> None:
    assert is_embedding_model("ollama_chat/qwen3-embedding:8b")
    assert is_embedding_model("mxbai-embed-large:latest")


def test_is_embedding_model_skips_chat_models() -> None:
    assert not is_embedding_model("ollama_chat/qwen3.5:35b")


def test_parse_ollama_models_filters_embedding_models() -> None:
    raw_models = [
        "qwen3.5:35b",
        {"name": "qwen3-embedding:8b"},
        {"model": "mxbai-embed-large:latest"},
    ]
    assert parse_ollama_models(raw_models) == ["ollama_chat/qwen3.5:35b"]
