"""OS-standard application data paths (issue #2)."""

from __future__ import annotations

from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

APP_NAME = "DocuWizard"
APP_AUTHOR = "DocuWizard"


def data_dir() -> Path:
    """Return the per-user data directory (projects, DB, files)."""
    return Path(user_data_dir(APP_NAME, APP_AUTHOR))


def config_dir() -> Path:
    """Return the per-user config directory."""
    return Path(user_config_dir(APP_NAME, APP_AUTHOR))


def projects_dir() -> Path:
    """Directory that holds project folders and copied source files."""
    return data_dir() / "projects"


def db_path() -> Path:
    """Primary SQLite database path."""
    return data_dir() / "docuwizard.db"


def config_path() -> Path:
    """JSON settings file path."""
    return config_dir() / "settings.json"


def ensure_app_dirs() -> None:
    """Create data/config directories if missing."""
    data_dir().mkdir(parents=True, exist_ok=True)
    config_dir().mkdir(parents=True, exist_ok=True)
    projects_dir().mkdir(parents=True, exist_ok=True)
