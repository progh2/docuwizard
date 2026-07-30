"""API key storage in a separate local file, outside settings.json (issue #33).

Keys live in the per-user config directory and never travel with the project.
"""

from __future__ import annotations

import json
import os
import stat

from docuwizard import paths

KNOWN_PROVIDERS = ("openai", "anthropic")


def secrets_path():
    return paths.config_dir() / "secrets.json"


def load_api_keys() -> dict[str, str]:
    path = secrets_path()
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if isinstance(v, str)}


def save_api_keys(keys: dict[str, str]) -> None:
    paths.ensure_app_dirs()
    path = secrets_path()
    cleaned = {k: v.strip() for k, v in keys.items() if v and v.strip()}
    with path.open("w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
        f.write("\n")
    if os.name == "posix":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600


def get_api_key(provider: str) -> str:
    return load_api_keys().get(provider, "")


def set_api_key(provider: str, key: str) -> None:
    keys = load_api_keys()
    keys[provider] = key
    save_api_keys(keys)
