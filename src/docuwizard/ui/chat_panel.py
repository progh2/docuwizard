"""Chat panel with conversation list and streaming answers (issues #18–#19)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from docuwizard.rag.orchestrator import RagAnswer
from docuwizard.rag.prompt import format_location
from docuwizard.services import conversations as conversation_service
from docuwizard.ui.chat_worker import ChatWorker


class ChatPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._project_id: str | None = None
        self._conversation_id: str | None = None
        self._worker: ChatWorker | None = None
        self._streaming_buffer = ""

        root = QHBoxLayout(self)
        splitter = QSplitter()

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("대화"))
        btn_row = QHBoxLayout()
        self.new_btn = QPushButton("새 대화")
        self.new_btn.clicked.connect(self.create_conversation)
        self.rename_btn = QPushButton("이름 변경")
        self.rename_btn.clicked.connect(self.rename_conversation)
        self.delete_btn = QPushButton("삭제")
        self.delete_btn.clicked.connect(self.delete_conversation)
        btn_row.addWidget(self.new_btn)
        btn_row.addWidget(self.rename_btn)
        btn_row.addWidget(self.delete_btn)
        left_layout.addLayout(btn_row)
        self.conversation_list = QListWidget()
        self.conversation_list.currentItemChanged.connect(self._on_conversation_selected)
        left_layout.addWidget(self.conversation_list)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.transcript = QPlainTextEdit()
        self.transcript.setReadOnly(True)
        self.citations = QPlainTextEdit()
        self.citations.setReadOnly(True)
        self.citations.setPlaceholderText("출처가 여기에 표시됩니다.")
        self.citations.setMaximumHeight(120)
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("질문을 입력하세요…")
        self.input.setMaximumHeight(90)
        send_row = QHBoxLayout()
        self.send_btn = QPushButton("질문하기")
        self.send_btn.clicked.connect(self.send_question)
        send_row.addStretch(1)
        send_row.addWidget(self.send_btn)
        right_layout.addWidget(self.transcript, stretch=3)
        right_layout.addWidget(QLabel("출처"))
        right_layout.addWidget(self.citations)
        right_layout.addWidget(self.input)
        right_layout.addLayout(send_row)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter)
        self.set_project(None)

    def set_project(self, project_id: str | None) -> None:
        self._project_id = project_id
        self._conversation_id = None
        enabled = project_id is not None
        self.new_btn.setEnabled(enabled)
        self.rename_btn.setEnabled(enabled)
        self.delete_btn.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        self.input.setEnabled(enabled)
        self.conversation_list.clear()
        self.transcript.clear()
        self.citations.clear()
        if project_id:
            self.refresh_conversations()

    def refresh_conversations(self) -> None:
        if not self._project_id:
            return
        current = self._conversation_id
        self.conversation_list.blockSignals(True)
        self.conversation_list.clear()
        for conversation in conversation_service.list_conversations(self._project_id):
            item = QListWidgetItem(conversation.title)
            item.setData(Qt.ItemDataRole.UserRole, conversation.id)
            self.conversation_list.addItem(item)
            if conversation.id == current:
                self.conversation_list.setCurrentItem(item)
        self.conversation_list.blockSignals(False)
        if self.conversation_list.currentItem() is None and self.conversation_list.count():
            self.conversation_list.setCurrentRow(0)
        elif self.conversation_list.currentItem() is None:
            self._conversation_id = None
            self.transcript.clear()

    def create_conversation(self) -> None:
        if not self._project_id:
            return
        conversation = conversation_service.create_conversation(self._project_id)
        self._conversation_id = conversation.id
        self.refresh_conversations()

    def rename_conversation(self) -> None:
        if not self._conversation_id:
            return
        conversation = conversation_service.get_conversation(self._conversation_id)
        title, ok = QInputDialog.getText(
            self, "대화 이름 변경", "제목:", text=conversation.title
        )
        if not ok:
            return
        conversation_service.rename_conversation(self._conversation_id, title)
        self.refresh_conversations()

    def delete_conversation(self) -> None:
        if not self._conversation_id:
            return
        answer = QMessageBox.question(
            self,
            "대화 삭제",
            "이 대화를 삭제할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        conversation_service.delete_conversation(self._conversation_id)
        self._conversation_id = None
        self.refresh_conversations()

    def send_question(self) -> None:
        if not self._project_id:
            return
        question = self.input.toPlainText().strip()
        if not question:
            return
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "안내", "응답 생성 중입니다.")
            return
        if not self._conversation_id:
            conversation = conversation_service.create_conversation(
                self._project_id, title=question[:40]
            )
            self._conversation_id = conversation.id
            self.refresh_conversations()

        conversation_service.add_message(
            self._conversation_id, role="user", content=question
        )
        self.input.clear()
        self._append_transcript("사용자", question)
        self.citations.clear()
        self._streaming_buffer = ""
        self._append_transcript("도우미", "")
        self.send_btn.setEnabled(False)
        self._worker = ChatWorker(self._project_id, question, parent=self)
        self._worker.token.connect(self._on_token)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_conversation_selected(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if current is None:
            self._conversation_id = None
            self.transcript.clear()
            return
        self._conversation_id = current.data(Qt.ItemDataRole.UserRole)
        self._load_messages()

    def _load_messages(self) -> None:
        self.transcript.clear()
        self.citations.clear()
        if not self._conversation_id:
            return
        for message in conversation_service.list_messages(self._conversation_id):
            label = "사용자" if message.role == "user" else "도우미"
            self._append_transcript(label, message.content)

    def _append_transcript(self, role: str, content: str) -> None:
        existing = self.transcript.toPlainText()
        block = f"[{role}]\n{content}\n"
        self.transcript.setPlainText((existing + "\n" + block).strip() + "\n")
        self.transcript.verticalScrollBar().setValue(
            self.transcript.verticalScrollBar().maximum()
        )

    def _on_token(self, token: str) -> None:
        self._streaming_buffer += token
        text = self.transcript.toPlainText()
        marker = "[도우미]\n"
        idx = text.rfind(marker)
        if idx < 0:
            return
        prefix = text[: idx + len(marker)]
        self.transcript.setPlainText(prefix + self._streaming_buffer + "\n")
        self.transcript.verticalScrollBar().setValue(
            self.transcript.verticalScrollBar().maximum()
        )

    def _on_finished(self, answer: RagAnswer) -> None:
        self.send_btn.setEnabled(True)
        if not self._conversation_id:
            return
        conversation_service.add_message(
            self._conversation_id,
            role="assistant",
            content=answer.text,
            model=answer.model,
            provider=answer.provider,
            citations=answer.citations,
        )
        self._load_messages()
        lines = []
        for i, chunk in enumerate(answer.citations, start=1):
            lines.append(f"[doc:{i}] {format_location(chunk)} (score={chunk.score:.3f})")
            snippet = chunk.text[:240] + ("…" if len(chunk.text) > 240 else "")
            lines.append(snippet)
            lines.append("")
        self.citations.setPlainText("\n".join(lines).strip() or "(관련 출처 없음)")
        conversation = conversation_service.get_conversation(self._conversation_id)
        if conversation.title == "새 대화":
            preview = answer.text[:40] or "대화"
            conversation_service.rename_conversation(self._conversation_id, preview)
            self.refresh_conversations()

    def _on_failed(self, message: str) -> None:
        self.send_btn.setEnabled(True)
        self._append_transcript("오류", message)
        QMessageBox.warning(self, "질의 실패", message)
