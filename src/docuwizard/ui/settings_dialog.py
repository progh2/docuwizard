"""Settings dialog with Ollama model dropdowns (issue #20)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
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

EMBED_HINTS = (
    "embed",
    "nomic",
    "bge",
    "e5",
    "minilm",
    "mxbai",
    "snowflake-arctic-embed",
)


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.resize(560, 340)
        self.settings = load_settings()
        self._models: list[str] = []

        layout = QVBoxLayout(self)
        form = QFormLayout()
        llm = self.settings.get("llm", {})
        rag = self.settings.get("rag", {})

        self.base_url = QLineEdit(str(llm.get("ollama_base_url", "")))
        self.chat_model = QComboBox()
        self.chat_model.setEditable(False)
        self.embed_model = QComboBox()
        self.embed_model.setEditable(False)
        self.top_k = QSpinBox()
        self.top_k.setRange(1, 20)
        self.top_k.setValue(int(rag.get("top_k", 5)))
        self.timeout_sec = QSpinBox()
        self.timeout_sec.setRange(30, 3600)
        self.timeout_sec.setSingleStep(30)
        self.timeout_sec.setSuffix(" 초")
        self.timeout_sec.setValue(int(llm.get("ollama_timeout_sec", 600)))

        form.addRow("Ollama URL", self.base_url)
        form.addRow("채팅 모델", self.chat_model)
        form.addRow("임베딩 모델", self.embed_model)
        form.addRow("검색 top_k", self.top_k)
        form.addRow("응답 타임아웃", self.timeout_sec)
        layout.addLayout(form)

        hint = QLabel(
            "채팅 모델(질문 답변)과 임베딩 모델(문서 검색용 벡터)은 서로 다릅니다.\n"
            "예: 채팅 gemma:2b(빠름) / gemma4:12b(느림), 임베딩 nomic-embed-text.\n"
            "12b급은 첫 응답까지 수 분이 걸릴 수 있으니 타임아웃을 충분히 두세요."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555;")
        layout.addWidget(hint)

        test_row = QHBoxLayout()
        self.refresh_btn = QPushButton("모델 목록 불러오기")
        self.refresh_btn.clicked.connect(self.refresh_models)
        self.test_btn = QPushButton("연결 테스트")
        self.test_btn.clicked.connect(self.test_connection)
        self.warmup_btn = QPushButton("채팅 모델 예열")
        self.warmup_btn.clicked.connect(self.warmup_chat_model)
        self.test_result = QLabel("")
        test_row.addWidget(self.refresh_btn)
        test_row.addWidget(self.test_btn)
        test_row.addWidget(self.warmup_btn)
        test_row.addWidget(self.test_result, stretch=1)
        layout.addLayout(test_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Seed combos with saved values, then try live refresh.
        saved_chat = str(llm.get("ollama_chat_model", ""))
        saved_embed = str(llm.get("ollama_embed_model", ""))
        self._set_combo_items(self.chat_model, [saved_chat] if saved_chat else [], saved_chat)
        self._set_combo_items(
            self.embed_model, [saved_embed] if saved_embed else [], saved_embed
        )
        self.refresh_models(show_errors=False)

    def _client_from_form(self) -> OllamaClient:
        return OllamaClient(
            OllamaConfig(
                base_url=self.base_url.text().strip(),
                chat_model=self.chat_model.currentText().strip(),
                embed_model=self.embed_model.currentText().strip(),
                timeout_sec=float(self.timeout_sec.value()),
            )
        )

    def refresh_models(self, show_errors: bool = True) -> None:
        try:
            models = self._client_from_form().list_models()
        except OllamaError as exc:
            self.test_result.setText(str(exc))
            if show_errors:
                QMessageBox.warning(self, "모델 목록 실패", str(exc))
            return

        self._models = models
        chat_candidates = [m for m in models if not self._looks_like_embed(m)] or models
        embed_candidates = [m for m in models if self._looks_like_embed(m)] or models
        saved_chat = self.chat_model.currentText().strip()
        saved_embed = self.embed_model.currentText().strip()
        self._set_combo_items(self.chat_model, chat_candidates, saved_chat)
        self._set_combo_items(self.embed_model, embed_candidates, saved_embed)
        self.test_result.setText(f"모델 {len(models)}개 불러옴")

    def test_connection(self) -> None:
        try:
            message = self._client_from_form().ping()
            self.test_result.setText(message)
            self.refresh_models(show_errors=False)
        except OllamaError as exc:
            self.test_result.setText(str(exc))
            QMessageBox.warning(self, "연결 실패", str(exc))

    def warmup_chat_model(self) -> None:
        client = self._client_from_form()
        self.test_result.setText(f"예열 중… ({client.config.chat_model})")
        try:
            message = client.warmup()
            self.test_result.setText(message)
            QMessageBox.information(self, "예열 완료", message)
        except OllamaError as exc:
            self.test_result.setText(str(exc))
            QMessageBox.warning(self, "예열 실패", str(exc))

    def save(self) -> None:
        chat = self.chat_model.currentText().strip()
        embed = self.embed_model.currentText().strip()
        if not chat or not embed:
            QMessageBox.warning(
                self,
                "저장 불가",
                "채팅/임베딩 모델을 선택하세요. ‘모델 목록 불러오기’를 먼저 눌러주세요.",
            )
            return
        self.settings.setdefault("llm", {})
        self.settings.setdefault("rag", {})
        self.settings["llm"]["ollama_base_url"] = self.base_url.text().strip()
        self.settings["llm"]["ollama_chat_model"] = chat
        self.settings["llm"]["ollama_embed_model"] = embed
        self.settings["llm"]["ollama_timeout_sec"] = int(self.timeout_sec.value())
        self.settings["rag"]["top_k"] = int(self.top_k.value())
        save_settings(self.settings)
        self.accept()

    @staticmethod
    def _looks_like_embed(name: str) -> bool:
        lower = name.casefold()
        return any(hint in lower for hint in EMBED_HINTS)

    @staticmethod
    def _set_combo_items(combo: QComboBox, items: list[str], preferred: str) -> None:
        combo.blockSignals(True)
        combo.clear()
        values = list(dict.fromkeys([*(items or []), preferred] if preferred else items))
        values = [v for v in values if v]
        combo.addItems(values)
        if preferred and preferred in values:
            combo.setCurrentText(preferred)
        elif values:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)
