"""Scrollable chat transcript with message bubbles."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class MessageBubble(QFrame):
    def __init__(self, role: str, content: str, parent=None) -> None:
        super().__init__(parent)
        self._role = role
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        role_label = QLabel(self._role_title(role))
        role_label.setObjectName("messageRole")
        self.body = QLabel(content)
        self.body.setWordWrap(True)
        self.body.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.body.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        if role == "user":
            self.setObjectName("messageUser")
            self.body.setObjectName("messageBodyUser")
            role_label.setStyleSheet("color: #ccfbf1;")
        elif role == "error":
            self.setObjectName("messageError")
            self.body.setObjectName("messageBody")
            role_label.setStyleSheet("color: #b91c1c;")
        else:
            self.setObjectName("messageAssistant")
            self.body.setObjectName("messageBody")

        layout.addWidget(role_label)
        layout.addWidget(self.body)
        self.setMaximumWidth(720)

    @staticmethod
    def _role_title(role: str) -> str:
        if role == "user":
            return "사용자"
        if role == "error":
            return "오류"
        if role.endswith("★") or "★" in role:
            return "도우미 ★"
        return "도우미"

    def set_content(self, content: str) -> None:
        self.body.setText(content)


class TranscriptView(QScrollArea):
    """Vertical stack of message bubbles with streaming support."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(12)
        self._layout.addStretch(1)
        self.setWidget(self._container)

        self._empty = QLabel(
            "대화를 선택하거나 새 대화를 만든 뒤\n질문을 입력하세요.\n"
            "Ctrl+Enter로 전송 · Esc로 중단"
        )
        self._empty.setObjectName("emptyState")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setWordWrap(True)
        self._layout.insertWidget(0, self._empty)

        self._bubbles: list[MessageBubble] = []
        self._streaming: MessageBubble | None = None

    def clear(self) -> None:
        while self._bubbles:
            bubble = self._bubbles.pop()
            self._layout.removeWidget(bubble)
            bubble.deleteLater()
        self._streaming = None
        self._empty.setVisible(True)

    def add_message(self, role: str, content: str, *, streaming: bool = False) -> MessageBubble:
        self._empty.setVisible(False)
        bubble = MessageBubble(role, content)
        # Insert before the trailing stretch.
        self._layout.insertWidget(self._layout.count() - 1, self._wrap(bubble, role))
        self._bubbles.append(bubble)
        if streaming:
            self._streaming = bubble
        self._scroll_to_bottom()
        return bubble

    def update_streaming(self, content: str) -> None:
        if self._streaming is None:
            return
        self._streaming.set_content(content or "…")
        self._scroll_to_bottom()

    def finish_streaming(self) -> None:
        self._streaming = None

    def _wrap(self, bubble: MessageBubble, role: str) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        if role == "user":
            row_layout.addStretch(1)
            row_layout.addWidget(bubble, stretch=0)
        else:
            row_layout.addWidget(bubble, stretch=0)
            row_layout.addStretch(1)
        return row

    def _scroll_to_bottom(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
