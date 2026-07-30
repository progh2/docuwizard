"""Qt application bootstrap."""

from __future__ import annotations

import sys


def run() -> int:
    """Create QApplication and show the main window."""
    from PySide6.QtWidgets import QApplication

    from docuwizard.db import init_db
    from docuwizard.paths import ensure_app_dirs
    from docuwizard.ui.main_window import MainWindow
    from docuwizard.ui.theme import apply_theme

    ensure_app_dirs()
    init_db()
    app = QApplication(sys.argv)
    app.setApplicationName("DocuWizard")
    app.setOrganizationName("DocuWizard")
    apply_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()
