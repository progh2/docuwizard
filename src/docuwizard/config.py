"""Load/save local application settings (issue #2)."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from docuwizard.paths import config_path, ensure_app_dirs

DEFAULT_SETTINGS: dict[str, Any] = {
    "llm": {
        "provider": "ollama",
        "ollama_base_url": "http://127.0.0.1:11434",
        "ollama_chat_model": "gemma2",
        "ollama_embed_model": "nomic-embed-text",
        "ollama_timeout_sec": 600,
        "openai_model": "gpt-4o-mini",
        "openai_base_url": "https://api.openai.com/v1",
        "anthropic_model": "claude-sonnet-4-5",
        "anthropic_base_url": "https://api.anthropic.com/v1",
    },
    "chunking": {
        "chunk_size": 800,
        "chunk_overlap": 120,
    },
    "rag": {
        "top_k": 5,
    },
    "ui": {
        "language": "ko",
    },
}


def load_settings() -> dict[str, Any]:
    """Load settings from disk, merging with defaults."""
    ensure_app_dirs()
    path = config_path()
    if not path.exists():
        settings = deepcopy(DEFAULT_SETTINGS)
        save_settings(settings)
        return settings
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return _deep_merge(deepcopy(DEFAULT_SETTINGS), data)


def save_settings(settings: dict[str, Any]) -> None:
    """Persist settings as UTF-8 JSON."""
    ensure_app_dirs()
    path = config_path()
    with path.open("w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base
