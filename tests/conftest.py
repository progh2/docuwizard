"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from docuwizard.db import init_db


@pytest.fixture(scope="session")
def qapp():
    """Shared QApplication for widget smoke tests."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(autouse=True)
def isolated_app_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data = tmp_path / "data"
    config = tmp_path / "config"
    projects = data / "projects"
    db = data / "docuwizard.db"

    monkeypatch.setattr("docuwizard.paths.data_dir", lambda: data)
    monkeypatch.setattr("docuwizard.paths.config_dir", lambda: config)
    monkeypatch.setattr("docuwizard.paths.projects_dir", lambda: projects)
    monkeypatch.setattr("docuwizard.paths.db_path", lambda: db)
    monkeypatch.setattr("docuwizard.services.projects.projects_dir", lambda: projects)
    monkeypatch.setattr("docuwizard.db.db_path", lambda: db)
    init_db(db)
    yield
