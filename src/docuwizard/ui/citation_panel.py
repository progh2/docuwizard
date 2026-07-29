"""Clickable citation list with preview dialog (issue #21)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from docuwizard.rag.prompt import format_location
from docuwizard.rag.vectors import RetrievedChunk


class CitationPreviewDialog(QDialog):
    def __init__(self, chunk: RetrievedChunk, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("출처 미리보기")
        self.resize(560, 360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(format_location(chunk)))
        body = QPlainTextEdit()
        body.setReadOnly(True)
        body.setPlainText(chunk.text)
        layout.addWidget(body)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)


class CitationPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("출처 (더블클릭하면 미리보기)"))
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._preview_item)
        layout.addWidget(self.list)
        self._chunks: list[RetrievedChunk] = []

    def clear(self) -> None:
        self._chunks = []
        self.list.clear()

    def set_chunks(self, chunks: list[RetrievedChunk]) -> None:
        self._chunks = list(chunks)
        self.list.clear()
        if not chunks:
            item = QListWidgetItem("(관련 출처 없음)")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(item)
            return
        for idx, chunk in enumerate(chunks, start=1):
            score = f" score={chunk.score:.3f}" if chunk.score else ""
            title = f"[doc:{idx}] {format_location(chunk)}{score}"
            snippet = chunk.text[:160] + ("…" if len(chunk.text) > 160 else "")
            item = QListWidgetItem(f"{title}\n{snippet}")
            item.setData(Qt.ItemDataRole.UserRole, idx - 1)
            item.setToolTip(chunk.text)
            self.list.addItem(item)

    def _preview_item(self, item: QListWidgetItem) -> None:
        index = item.data(Qt.ItemDataRole.UserRole)
        if index is None or not isinstance(index, int):
            return
        if index < 0 or index >= len(self._chunks):
            return
        dialog = CitationPreviewDialog(self._chunks[index], self)
        dialog.exec()
