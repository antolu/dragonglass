from __future__ import annotations

from dragonglass.agent.runtime import build_completion_kwargs


def test_ollama_model_includes_api_base() -> None:
    kwargs = build_completion_kwargs("ollama_chat/llama3.2", "http://localhost:11434")
    assert kwargs["api_base"] == "http://localhost:11434"


def test_gemini_model_excludes_api_base() -> None:
    kwargs = build_completion_kwargs(
        "gemini/gemini-2.0-flash", "http://localhost:11434"
    )
    assert "api_base" not in kwargs


def test_openai_model_excludes_api_base() -> None:
    kwargs = build_completion_kwargs("openai/gpt-4o-mini", "http://localhost:11434")
    assert "api_base" not in kwargs


def test_anthropic_model_excludes_api_base() -> None:
    kwargs = build_completion_kwargs(
        "anthropic/claude-3-5-sonnet-20241022", "http://localhost:11434"
    )
    assert "api_base" not in kwargs


def test_ollama_prefix_includes_api_base() -> None:
    kwargs = build_completion_kwargs("ollama/llama3.2", "http://localhost:11434")
    assert kwargs["api_base"] == "http://localhost:11434"
