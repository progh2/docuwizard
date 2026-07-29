"""Qt application bootstrap."""

from __future__ import annotations

import sys


def run() -> int:
    """Create QApplication and show the main window."""
    from PySide6.QtWidgets import QApplication

    from docuwizard.paths import ensure_app_dirs
    from docuwizard.ui.main_window import MainWindow

    ensure_app_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName("DocuWizard")
    app.setOrganizationName("DocuWizard")
    window = MainWindow()
    window.show()
    return app.exec()
