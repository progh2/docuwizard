"""Chat panel with bubble transcript, search, stars, citations."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
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
from docuwizard.services import conversations as conversation_service
from docuwizard.ui.chat_worker import ChatWorker
from docuwizard.ui.citation_panel import CitationPanel
from docuwizard.ui.message_view import TranscriptView


class ChatPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._project_id: str | None = None
        self._conversation_id: str | None = None
        self._worker: ChatWorker | None = None
        self._streaming_buffer = ""
        self._messages: list = []
        self._favorites_callback = None

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        splitter = QSplitter()

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)
        section = QLabel("대화")
        section.setObjectName("sectionTitle")
        left_layout.addWidget(section)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("대화·내용 검색…")
        self.search_edit.textChanged.connect(self.refresh_conversations)
        left_layout.addWidget(self.search_edit)

        btn_row = QHBoxLayout()
        self.new_btn = QPushButton("새 대화")
        self.new_btn.clicked.connect(self.create_conversation)
        self.rename_btn = QPushButton("이름 변경")
        self.rename_btn.clicked.connect(self.rename_conversation)
        self.star_btn = QPushButton("★")
        self.star_btn.setToolTip("대화 즐겨찾기")
        self.star_btn.clicked.connect(self.toggle_conversation_star)
        self.delete_btn = QPushButton("삭제")
        self.delete_btn.setObjectName("dangerButton")
        self.delete_btn.clicked.connect(self.delete_conversation)
        btn_row.addWidget(self.new_btn)
        btn_row.addWidget(self.rename_btn)
        btn_row.addWidget(self.star_btn)
        btn_row.addWidget(self.delete_btn)
        left_layout.addLayout(btn_row)
        self.conversation_list = QListWidget()
        self.conversation_list.currentItemChanged.connect(self._on_conversation_selected)
        left_layout.addWidget(self.conversation_list)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        msg_btn_row = QHBoxLayout()
        self.star_message_btn = QPushButton("★ 마지막 답변")
        self.star_message_btn.clicked.connect(self.toggle_last_answer_star)
        msg_btn_row.addWidget(self.star_message_btn)
        msg_btn_row.addStretch(1)
        right_layout.addLayout(msg_btn_row)

        self.transcript = TranscriptView()
        self.citation_panel = CitationPanel()
        self.citation_panel.setMaximumHeight(160)
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("질문을 입력하세요…  (Ctrl+Enter 전송)")
        self.input.setMaximumHeight(100)
        send_row = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")
        self.stop_btn = QPushButton("중단")
        self.stop_btn.setToolTip("Esc")
        self.stop_btn.clicked.connect(self.stop_answer)
        self.stop_btn.setEnabled(False)
        self.send_btn = QPushButton("질문하기")
        self.send_btn.setObjectName("primaryButton")
        self.send_btn.setToolTip("Ctrl+Enter")
        self.send_btn.clicked.connect(self.send_question)
        send_row.addWidget(self.status_label, stretch=1)
        send_row.addWidget(self.stop_btn)
        send_row.addWidget(self.send_btn)
        right_layout.addWidget(self.transcript, stretch=3)
        right_layout.addWidget(self.citation_panel)
        right_layout.addWidget(self.input)
        right_layout.addLayout(send_row)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter)

        QShortcut(QKeySequence("Ctrl+Return"), self.input, activated=self.send_question)
        QShortcut(QKeySequence("Ctrl+Enter"), self.input, activated=self.send_question)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self.stop_answer)

        self.set_project(None)

    def set_favorites_callback(self, callback) -> None:
        self._favorites_callback = callback

    def set_project(self, project_id: str | None) -> None:
        self._project_id = project_id
        self._conversation_id = None
        enabled = project_id is not None
        for widget in (
            self.new_btn,
            self.rename_btn,
            self.star_btn,
            self.delete_btn,
            self.send_btn,
            self.input,
            self.search_edit,
            self.star_message_btn,
        ):
            widget.setEnabled(enabled)
        self.conversation_list.clear()
        self.transcript.clear()
        self.citation_panel.clear()
        self._messages = []
        if project_id:
            self.refresh_conversations()

    def open_conversation(self, conversation_id: str) -> None:
        self._conversation_id = conversation_id
        self.search_edit.clear()
        self.refresh_conversations()
        for i in range(self.conversation_list.count()):
            item = self.conversation_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == conversation_id:
                self.conversation_list.setCurrentItem(item)
                break

    def refresh_conversations(self) -> None:
        if not self._project_id:
            return
        current = self._conversation_id
        query = self.search_edit.text().strip() or None
        self.conversation_list.blockSignals(True)
        self.conversation_list.clear()
        for conversation in conversation_service.list_conversations(
            self._project_id, query=query
        ):
            prefix = "★ " if conversation.is_starred else ""
            item = QListWidgetItem(f"{prefix}{conversation.title}")
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
            self.citation_panel.clear()

    def create_conversation(self) -> None:
        if not self._project_id:
            return
        conversation = conversation_service.create_conversation(self._project_id)
        self._conversation_id = conversation.id
        self.refresh_conversations()
        self._notify_favorites()

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
        self._notify_favorites()

    def toggle_conversation_star(self) -> None:
        if not self._conversation_id:
            return
        conversation_service.toggle_conversation_star(self._conversation_id)
        self.refresh_conversations()
        self._notify_favorites()

    def toggle_last_answer_star(self) -> None:
        answers = [m for m in self._messages if m.role == "assistant"]
        if not answers:
            QMessageBox.information(self, "안내", "별표를 달 답변이 없습니다.")
            return
        conversation_service.toggle_message_star(answers[-1].id)
        self._load_messages()
        self._notify_favorites()

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
        self._notify_favorites()

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

        history = [
            {"role": m.role, "content": m.content}
            for m in self._messages
            if m.role in ("user", "assistant")
        ]
        conversation_service.add_message(
            self._conversation_id, role="user", content=question
        )
        self.input.clear()
        self.transcript.add_message("user", question)
        self.citation_panel.clear()
        self._streaming_buffer = ""
        self.transcript.add_message("assistant", "…", streaming=True)
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("준비 중…")
        self._worker = ChatWorker(
            self._project_id, question, history=history, parent=self
        )
        self._worker.token.connect(self._on_token)
        self._worker.status.connect(self._on_status)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def stop_answer(self) -> None:
        if self._worker and self._worker.isRunning():
            self.stop_btn.setEnabled(False)
            self.status_label.setText("중단 요청됨…")
            self._worker.cancel()

    def _notify_favorites(self) -> None:
        if self._favorites_callback:
            self._favorites_callback()

    def _on_conversation_selected(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if current is None:
            self._conversation_id = None
            self.transcript.clear()
            self.citation_panel.clear()
            return
        self._conversation_id = current.data(Qt.ItemDataRole.UserRole)
        self._load_messages()

    def _load_messages(self) -> None:
        self.transcript.clear()
        self.citation_panel.clear()
        self._messages = []
        if not self._conversation_id:
            return
        self._messages = conversation_service.list_messages(self._conversation_id)
        if not self._messages:
            return
        for message in self._messages:
            if message.role == "user":
                role = "user"
            elif message.is_starred:
                role = "assistant★"
            else:
                role = "assistant"
            self.transcript.add_message(role, message.content)
        last_answer = next(
            (m for m in reversed(self._messages) if m.role == "assistant"),
            None,
        )
        if last_answer and last_answer.citation_ids:
            chunks = conversation_service.get_chunks_by_ids(last_answer.citation_ids)
            self.citation_panel.set_chunks(chunks)

    def _on_status(self, message: str) -> None:
        self.status_label.setText(message)

    def _on_token(self, token: str) -> None:
        self._streaming_buffer += token
        self.transcript.update_streaming(self._streaming_buffer)

    def _on_finished(self, answer: RagAnswer) -> None:
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.transcript.finish_streaming()
        self.status_label.setText(f"완료 · {answer.model}")
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
        self.citation_panel.set_chunks(answer.citations)
        conversation = conversation_service.get_conversation(self._conversation_id)
        if conversation.title == "새 대화":
            preview = answer.text[:40] or "대화"
            conversation_service.rename_conversation(self._conversation_id, preview)
            self.refresh_conversations()

    def _on_cancelled(self, partial: str) -> None:
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.transcript.finish_streaming()
        self.status_label.setText("중단됨")
        if self._conversation_id and partial.strip():
            conversation_service.add_message(
                self._conversation_id,
                role="assistant",
                content=partial.strip() + "\n\n(응답이 중단되었습니다)",
            )
        if self._conversation_id:
            self._load_messages()

    def _on_failed(self, message: str) -> None:
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.transcript.finish_streaming()
        self.status_label.setText("실패")
        self.transcript.add_message("error", message)
        QMessageBox.warning(self, "질의 실패", message)
