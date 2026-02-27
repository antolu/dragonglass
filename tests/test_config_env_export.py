from __future__ import annotations

import os

import pytest

import dragonglass.config


def test_re_export_settings_exports_only_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("SELECTED_MODEL", raising=False)
    monkeypatch.delenv("DG_TEST_ENV", raising=False)

    settings = dragonglass.config.Settings(
        llm_model="ollama_chat/qwen3.5:27b",
        selected_model="ollama_chat/qwen3.5:35b",
        env_vars={"DG_TEST_ENV": "ok"},
    )
    dragonglass.config.re_export_settings(settings)

    assert os.environ.get("DG_TEST_ENV") == "ok"
    assert "LLM_MODEL" not in os.environ
    assert "SELECTED_MODEL" not in os.environ
