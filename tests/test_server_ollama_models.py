from __future__ import annotations

from dragonglass.agent.types import JsonValue
from dragonglass.server.server import (
    is_embedding_model,
    parse_ollama_models,
)


def test_is_embedding_model_detects_embedding_tags() -> None:
    assert is_embedding_model("qwen3-embedding:8b")
    assert is_embedding_model("mxbai-embed-large:latest")


def test_is_embedding_model_skips_chat_models() -> None:
    assert not is_embedding_model("qwen3.5:35b")


def test_parse_ollama_models_uses_ollama_display_prefix() -> None:
    raw_models: JsonValue = [
        "qwen3.5:35b",
        {"name": "qwen2.5:7b"},
    ]
    assert parse_ollama_models(raw_models) == [
        "ollama/qwen3.5:35b",
        "ollama/qwen2.5:7b",
    ]


def test_parse_ollama_models_filters_embedding_models() -> None:
    raw_models: JsonValue = [
        "qwen3.5:35b",
        {"name": "qwen3-embedding:8b"},
        {"model": "mxbai-embed-large:latest"},
    ]
    assert parse_ollama_models(raw_models) == ["ollama/qwen3.5:35b"]


def test_parse_ollama_models_normalises_existing_prefix() -> None:
    raw_models: JsonValue = [
        "ollama_chat/qwen3.5:35b",
        "ollama/qwen2.5:7b",
    ]
    assert parse_ollama_models(raw_models) == [
        "ollama/qwen3.5:35b",
        "ollama/qwen2.5:7b",
    ]
