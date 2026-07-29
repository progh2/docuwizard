"""Tests for Ollama client config and helpers."""

from __future__ import annotations

from docuwizard.llm.ollama import OllamaConfig


def test_from_settings_uses_selected_chat_and_embed_models() -> None:
    settings = {
        "llm": {
            "ollama_base_url": "http://127.0.0.1:11434",
            "ollama_chat_model": "gemma3:12b",
            "ollama_embed_model": "nomic-embed-text",
            "ollama_timeout_sec": 900,
        }
    }
    cfg = OllamaConfig.from_settings(settings)
    assert cfg.chat_model == "gemma3:12b"
    assert cfg.embed_model == "nomic-embed-text"
    assert cfg.timeout_sec == 900


def test_looks_like_embed_helpers() -> None:
    from docuwizard.ui.settings_dialog import SettingsDialog

    assert SettingsDialog._looks_like_embed("nomic-embed-text")
    assert SettingsDialog._looks_like_embed("mxbai-embed-large")
    assert not SettingsDialog._looks_like_embed("gemma3:12b")
    assert not SettingsDialog._looks_like_embed("llama3.2")
