"""UI smoke tests for theme and chat transcript bubbles."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from docuwizard.ui.message_view import TranscriptView
from docuwizard.ui.theme import APP_STYLESHEET, apply_theme


def test_apply_theme_sets_stylesheet(qapp: QApplication) -> None:
    apply_theme(qapp)
    assert "QPushButton#primaryButton" in qapp.styleSheet()
    assert APP_STYLESHEET[:20] in qapp.styleSheet()


def test_transcript_view_adds_and_streams(qapp: QApplication) -> None:
    view = TranscriptView()
    view.add_message("user", "마감일은?")
    view.add_message("assistant", "", streaming=True)
    view.update_streaming("금요일입니다.")
    view.finish_streaming()
    assert len(view._bubbles) == 2
    assert view._bubbles[-1].body.text() == "금요일입니다."
    view.clear()
    assert view._bubbles == []
