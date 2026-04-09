from __future__ import annotations

from dragonglass.agent import resolve_model_name


def test_resolve_model_name_returns_default_without_override() -> None:
    assert resolve_model_name(None, "ollama/llama3.2") == "ollama/llama3.2"


def test_resolve_model_name_strips_override_and_applies_provider_prefix() -> None:
    assert (
        resolve_model_name("  qwen3.5:27b  ", "ollama/llama3.2") == "ollama/qwen3.5:27b"
    )


def test_resolve_model_name_preserves_explicit_provider() -> None:
    assert (
        resolve_model_name("openai/gpt-4o-mini", "ollama/llama3.2")
        == "openai/gpt-4o-mini"
    )


def test_resolve_model_name_preserves_ollama_chat_provider() -> None:
    assert (
        resolve_model_name("ollama_chat/qwen3.5:27b", "ollama/llama3.2")
        == "ollama_chat/qwen3.5:27b"
    )


def test_resolve_model_name_falls_back_on_blank_override() -> None:
    assert resolve_model_name("   ", "ollama/llama3.2") == "ollama/llama3.2"
