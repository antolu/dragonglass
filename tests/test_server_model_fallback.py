from __future__ import annotations

from dragonglass.server.server import resolve_chat_model


def test_resolve_chat_model_uses_selected_model_when_override_missing() -> None:
    assert (
        resolve_chat_model(None, "ollama_chat/qwen3.5:35b") == "ollama_chat/qwen3.5:35b"
    )


def test_resolve_chat_model_prefers_explicit_override() -> None:
    assert (
        resolve_chat_model("ollama_chat/qwen3.5:35b", "ollama_chat/qwen3.5:27b")
        == "ollama_chat/qwen3.5:35b"
    )


def test_resolve_chat_model_trims_and_falls_back() -> None:
    assert (
        resolve_chat_model("   ", "  ollama_chat/qwen3.5:35b  ")
        == "ollama_chat/qwen3.5:35b"
    )
