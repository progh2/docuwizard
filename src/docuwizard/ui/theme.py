"""Application-wide visual theme (light workspace look)."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

# Calm slate + teal accent — readable for long document Q&A sessions.
APP_STYLESHEET = """
QWidget {
    font-size: 13px;
    color: #1f2937;
}
QMainWindow, QDialog {
    background: #f3f5f7;
}
QToolBar {
    background: #ffffff;
    border-bottom: 1px solid #d8dee6;
    spacing: 8px;
    padding: 6px 10px;
}
QToolBar QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 12px;
    color: #1f2937;
}
QToolBar QToolButton:hover {
    background: #eef2f6;
    border-color: #d8dee6;
}
QToolBar QToolButton:pressed {
    background: #e2e8f0;
}
QSplitter::handle {
    background: #d8dee6;
    width: 1px;
}
QTabWidget::pane {
    border: 1px solid #d8dee6;
    border-radius: 8px;
    background: #ffffff;
    top: -1px;
}
QTabBar::tab {
    background: #e8edf2;
    border: 1px solid #d8dee6;
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    color: #4b5563;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #0f766e;
    font-weight: 600;
}
QTabBar::tab:hover:!selected {
    background: #f1f5f9;
}
QListWidget {
    background: #ffffff;
    border: 1px solid #d8dee6;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}
QListWidget::item {
    padding: 8px 10px;
    border-radius: 6px;
    margin: 1px 0;
}
QListWidget::item:selected {
    background: #ccfbf1;
    color: #134e4a;
}
QListWidget::item:hover:!selected {
    background: #f1f5f9;
}
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QComboBox {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: #99f6e4;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QSpinBox:focus, QComboBox:focus {
    border-color: #0d9488;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 7px 14px;
    min-height: 18px;
}
QPushButton:hover {
    background: #f8fafc;
    border-color: #94a3b8;
}
QPushButton:pressed {
    background: #e2e8f0;
}
QPushButton:disabled {
    color: #94a3b8;
    background: #f1f5f9;
}
QPushButton#primaryButton {
    background: #0d9488;
    border-color: #0f766e;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background: #0f766e;
}
QPushButton#primaryButton:disabled {
    background: #99f6e4;
    border-color: #5eead4;
    color: #f0fdfa;
}
QPushButton#dangerButton {
    color: #b91c1c;
    border-color: #fecaca;
}
QPushButton#dangerButton:hover {
    background: #fef2f2;
}
QProgressBar {
    border: 1px solid #d8dee6;
    border-radius: 6px;
    background: #eef2f6;
    text-align: center;
    height: 14px;
}
QProgressBar::chunk {
    background: #14b8a6;
    border-radius: 5px;
}
QGroupBox {
    border: 1px solid #d8dee6;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    background: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #0f766e;
    font-weight: 600;
}
QScrollArea {
    border: none;
    background: transparent;
}
QLabel#sectionTitle {
    font-size: 12px;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 0.4px;
}
QLabel#pageTitle {
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
}
QLabel#muted {
    color: #64748b;
}
QLabel#emptyState {
    color: #94a3b8;
    font-size: 14px;
    padding: 24px;
}
QLabel#warningBanner {
    color: #92400e;
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 8px;
    padding: 8px 10px;
}
QFrame#messageUser {
    background: #0d9488;
    border-radius: 14px;
    border-top-right-radius: 4px;
}
QFrame#messageAssistant {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    border-top-left-radius: 4px;
}
QFrame#messageError {
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 14px;
}
QLabel#messageRole {
    font-size: 11px;
    font-weight: 700;
    color: #64748b;
}
QLabel#messageBody {
    font-size: 13px;
    color: #1f2937;
}
QLabel#messageBodyUser {
    font-size: 13px;
    color: #ffffff;
}
"""


def apply_theme(app: QApplication) -> None:
    """Apply Fusion style + DocuWizard stylesheet and default font."""
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    if not font.exactMatch():
        font = QFont()
        font.setPointSize(10)
    app.setFont(font)
    app.setStyleSheet(APP_STYLESHEET)
