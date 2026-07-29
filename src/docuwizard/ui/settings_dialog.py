"""Settings dialog with Ollama connection test (issue #20)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from docuwizard.config import load_settings, save_settings
from docuwizard.llm.ollama import OllamaClient, OllamaConfig, OllamaError


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.resize(480, 280)
        self.settings = load_settings()

        layout = QVBoxLayout(self)
        form = QFormLayout()
        llm = self.settings.get("llm", {})
        rag = self.settings.get("rag", {})

        self.base_url = QLineEdit(str(llm.get("ollama_base_url", "")))
        self.chat_model = QLineEdit(str(llm.get("ollama_chat_model", "")))
        self.embed_model = QLineEdit(str(llm.get("ollama_embed_model", "")))
        self.top_k = QSpinBox()
        self.top_k.setRange(1, 20)
        self.top_k.setValue(int(rag.get("top_k", 5)))

        form.addRow("Ollama URL", self.base_url)
        form.addRow("채팅 모델", self.chat_model)
        form.addRow("임베딩 모델", self.embed_model)
        form.addRow("검색 top_k", self.top_k)
        layout.addLayout(form)

        test_row = QHBoxLayout()
        self.test_btn = QPushButton("연결 테스트")
        self.test_btn.clicked.connect(self.test_connection)
        self.test_result = QLabel("")
        test_row.addWidget(self.test_btn)
        test_row.addWidget(self.test_result, stretch=1)
        layout.addLayout(test_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def test_connection(self) -> None:
        client = OllamaClient(
            OllamaConfig(
                base_url=self.base_url.text().strip(),
                chat_model=self.chat_model.text().strip(),
                embed_model=self.embed_model.text().strip(),
            )
        )
        try:
            message = client.ping()
            self.test_result.setText(message)
        except OllamaError as exc:
            self.test_result.setText(str(exc))
            QMessageBox.warning(self, "연결 실패", str(exc))

    def save(self) -> None:
        self.settings.setdefault("llm", {})
        self.settings.setdefault("rag", {})
        self.settings["llm"]["ollama_base_url"] = self.base_url.text().strip()
        self.settings["llm"]["ollama_chat_model"] = self.chat_model.text().strip()
        self.settings["llm"]["ollama_embed_model"] = self.embed_model.text().strip()
        self.settings["rag"]["top_k"] = int(self.top_k.value())
        save_settings(self.settings)
        self.accept()
