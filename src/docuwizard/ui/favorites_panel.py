"""Favorites view for starred conversations and answers (issue #24)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from docuwizard.services import conversations as conversation_service
from docuwizard.services import essentials as essentials_service


class FavoritesPanel(QWidget):
    open_conversation = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._project_id: str | None = None
        layout = QVBoxLayout(self)
        title = QLabel("즐겨찾기")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        hint = QLabel("★ 표시한 대화·답변·필수 포인트")
        hint.setObjectName("muted")
        layout.addWidget(hint)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._on_activate)
        layout.addWidget(self.list)
        self.set_project(None)

    def set_project(self, project_id: str | None) -> None:
        self._project_id = project_id
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        if not self._project_id:
            self.list.addItem(QListWidgetItem("프로젝트를 선택하세요"))
            return

        conversations = conversation_service.list_starred_conversations(self._project_id)
        messages = conversation_service.list_starred_messages(self._project_id)
        essentials = essentials_service.list_starred_items(self._project_id)
        if not conversations and not messages and not essentials:
            self.list.addItem(QListWidgetItem("(즐겨찾기 없음)"))
            return

        if conversations:
            header = QListWidgetItem("— ★ 대화 —")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(header)
            for conversation in conversations:
                item = QListWidgetItem(f"★ {conversation.title}")
                item.setData(Qt.ItemDataRole.UserRole, conversation.id)
                item.setToolTip(conversation.updated_at)
                self.list.addItem(item)

        if messages:
            header = QListWidgetItem("— ★ 답변 —")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(header)
            for favorite in messages:
                preview = favorite.message.content.replace("\n", " ")[:120]
                item = QListWidgetItem(f"★ [{favorite.conversation_title}] {preview}")
                item.setData(Qt.ItemDataRole.UserRole, favorite.conversation_id)
                item.setToolTip(favorite.message.content)
                self.list.addItem(item)

        if essentials:
            header = QListWidgetItem("— ★ 필수 포인트 —")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(header)
            for starred in essentials:
                entry = starred.item
                text = f"★ [{entry.category_name} · v{starred.report_version}] {entry.summary}"
                item = QListWidgetItem(text[:160])
                item.setToolTip(entry.summary)
                self.list.addItem(item)

    def _on_activate(self, item: QListWidgetItem) -> None:
        conversation_id = item.data(Qt.ItemDataRole.UserRole)
        if conversation_id:
            self.open_conversation.emit(str(conversation_id))
