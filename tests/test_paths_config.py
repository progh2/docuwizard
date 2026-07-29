"""Tests for OS data paths and settings."""

from __future__ import annotations

from pathlib import Path

from docuwizard import config, paths


def test_ensure_app_dirs_creates_directories(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(paths, "config_dir", lambda: tmp_path / "config")
    monkeypatch.setattr(paths, "projects_dir", lambda: tmp_path / "data" / "projects")

    paths.ensure_app_dirs()

    assert (tmp_path / "data").is_dir()
    assert (tmp_path / "config").is_dir()
    assert (tmp_path / "data" / "projects").is_dir()


def test_load_save_settings_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(paths, "config_dir", lambda: tmp_path / "config")
    monkeypatch.setattr(paths, "projects_dir", lambda: tmp_path / "data" / "projects")
    monkeypatch.setattr(paths, "config_path", lambda: tmp_path / "config" / "settings.json")

    settings = config.load_settings()
    assert settings["llm"]["provider"] == "ollama"
    settings["llm"]["ollama_chat_model"] = "gemma2:test"
    config.save_settings(settings)

    reloaded = config.load_settings()
    assert reloaded["llm"]["ollama_chat_model"] == "gemma2:test"


def test_version_importable() -> None:
    from docuwizard import __version__

    assert __version__
