"""Settings dialog: Ollama models, provider selection, API keys (#20, #33)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from docuwizard import apikeys
from docuwizard.config import load_settings, save_settings
from docuwizard.llm.base import LlmError
from docuwizard.llm.external import AnthropicClient, OpenAIClient
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

PROVIDER_LABELS = {
    "ollama": "Ollama (로컬, 기본)",
    "openai": "OpenAI (외부 API)",
    "anthropic": "Anthropic (외부 API)",
}

EXTERNAL_WARNING = (
    "⚠ 외부 API를 선택하면 질문과 검색된 문서 조각이 해당 제공자 서버로 "
    "전송됩니다. 민감한 문서는 Ollama(로컬)를 사용하세요. "
    "임베딩(문서 색인)은 항상 로컬 Ollama에서 수행됩니다."
)


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.resize(600, 560)
        self.settings = load_settings()
        self._keys = apikeys.load_api_keys()
        self._models: list[str] = []

        layout = QVBoxLayout(self)
        llm = self.settings.get("llm", {})
        rag = self.settings.get("rag", {})

        # --- Provider selection -------------------------------------------
        provider_form = QFormLayout()
        self.provider = QComboBox()
        for key, label in PROVIDER_LABELS.items():
            self.provider.addItem(label, key)
        saved_provider = str(llm.get("provider", "ollama"))
        index = self.provider.findData(saved_provider)
        self.provider.setCurrentIndex(index if index >= 0 else 0)
        self.provider.currentIndexChanged.connect(self._on_provider_changed)
        provider_form.addRow("답변 생성 프로바이더", self.provider)
        layout.addLayout(provider_form)

        self.external_warning = QLabel(EXTERNAL_WARNING)
        self.external_warning.setWordWrap(True)
        self.external_warning.setStyleSheet(
            "color: #8a4b00; background: #fff4e0; padding: 6px; border-radius: 4px;"
        )
        layout.addWidget(self.external_warning)

        # --- Ollama (local) ------------------------------------------------
        ollama_group = QGroupBox("Ollama (로컬 — 임베딩은 항상 여기서 수행)")
        form = QFormLayout(ollama_group)
        self.base_url = QLineEdit(str(llm.get("ollama_base_url", "")))
        self.chat_model = QComboBox()
        self.chat_model.setEditable(False)
        self.embed_model = QComboBox()
        self.embed_model.setEditable(False)
        self.timeout_sec = QSpinBox()
        self.timeout_sec.setRange(30, 3600)
        self.timeout_sec.setSingleStep(30)
        self.timeout_sec.setSuffix(" 초")
        self.timeout_sec.setValue(int(llm.get("ollama_timeout_sec", 600)))
        form.addRow("Ollama URL", self.base_url)
        form.addRow("채팅 모델", self.chat_model)
        form.addRow("임베딩 모델", self.embed_model)
        form.addRow("응답 타임아웃", self.timeout_sec)

        test_row = QHBoxLayout()
        self.refresh_btn = QPushButton("모델 목록 불러오기")
        self.refresh_btn.clicked.connect(self.refresh_models)
        self.test_btn = QPushButton("연결 테스트")
        self.test_btn.clicked.connect(self.test_connection)
        self.warmup_btn = QPushButton("채팅 모델 예열")
        self.warmup_btn.clicked.connect(self.warmup_chat_model)
        test_row.addWidget(self.refresh_btn)
        test_row.addWidget(self.test_btn)
        test_row.addWidget(self.warmup_btn)
        form.addRow(test_row)
        layout.addWidget(ollama_group)

        # --- External providers --------------------------------------------
        external_group = QGroupBox("외부 API (선택)")
        ext_form = QFormLayout(external_group)
        self.openai_model = QLineEdit(str(llm.get("openai_model", "gpt-4o-mini")))
        self.openai_key = QLineEdit(self._keys.get("openai", ""))
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key.setPlaceholderText("sk-…")
        self.anthropic_model = QLineEdit(
            str(llm.get("anthropic_model", "claude-sonnet-4-5"))
        )
        self.anthropic_key = QLineEdit(self._keys.get("anthropic", ""))
        self.anthropic_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.anthropic_key.setPlaceholderText("sk-ant-…")
        ext_form.addRow("OpenAI 모델", self.openai_model)
        ext_form.addRow("OpenAI API 키", self.openai_key)
        ext_form.addRow("Anthropic 모델", self.anthropic_model)
        ext_form.addRow("Anthropic API 키", self.anthropic_key)
        self.external_test_btn = QPushButton("외부 API 연결 테스트")
        self.external_test_btn.clicked.connect(self.test_external)
        ext_form.addRow(self.external_test_btn)
        layout.addWidget(external_group)

        # --- RAG ------------------------------------------------------------
        rag_form = QFormLayout()
        self.top_k = QSpinBox()
        self.top_k.setRange(1, 20)
        self.top_k.setValue(int(rag.get("top_k", 5)))
        rag_form.addRow("검색 top_k", self.top_k)
        layout.addLayout(rag_form)

        self.test_result = QLabel("")
        self.test_result.setWordWrap(True)
        layout.addWidget(self.test_result)

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
        self._on_provider_changed()
        self.refresh_models(show_errors=False)

    def selected_provider(self) -> str:
        return str(self.provider.currentData() or "ollama")

    def _on_provider_changed(self, _index: int = 0) -> None:
        self.external_warning.setVisible(self.selected_provider() != "ollama")

    def _client_from_form(self) -> OllamaClient:
        return OllamaClient(
            OllamaConfig(
                base_url=self.base_url.text().strip(),
                chat_model=self.chat_model.currentText().strip(),
                embed_model=self.embed_model.currentText().strip(),
                timeout_sec=float(self.timeout_sec.value()),
            )
        )

    def _external_client_from_form(self, provider: str):
        if provider == "openai":
            return OpenAIClient(
                model=self.openai_model.text().strip(),
                api_key=self.openai_key.text().strip(),
            )
        return AnthropicClient(
            model=self.anthropic_model.text().strip(),
            api_key=self.anthropic_key.text().strip(),
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

    def test_external(self) -> None:
        provider = self.selected_provider()
        if provider == "ollama":
            # Test whichever external provider has a key filled in.
            provider = "openai" if self.openai_key.text().strip() else "anthropic"
        client = self._external_client_from_form(provider)
        self.test_result.setText(f"{provider} 연결 확인 중…")
        try:
            message = client.ping()
            self.test_result.setText(message)
            QMessageBox.information(self, "연결 성공", message)
        except LlmError as exc:
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
        provider = self.selected_provider()
        if provider == "openai" and not self.openai_key.text().strip():
            QMessageBox.warning(self, "저장 불가", "OpenAI API 키를 입력하세요.")
            return
        if provider == "anthropic" and not self.anthropic_key.text().strip():
            QMessageBox.warning(self, "저장 불가", "Anthropic API 키를 입력하세요.")
            return

        self.settings.setdefault("llm", {})
        self.settings.setdefault("rag", {})
        self.settings["llm"]["provider"] = provider
        self.settings["llm"]["ollama_base_url"] = self.base_url.text().strip()
        self.settings["llm"]["ollama_chat_model"] = chat
        self.settings["llm"]["ollama_embed_model"] = embed
        self.settings["llm"]["ollama_timeout_sec"] = int(self.timeout_sec.value())
        self.settings["llm"]["openai_model"] = self.openai_model.text().strip()
        self.settings["llm"]["anthropic_model"] = self.anthropic_model.text().strip()
        self.settings["rag"]["top_k"] = int(self.top_k.value())
        save_settings(self.settings)
        apikeys.save_api_keys(
            {
                **self._keys,
                "openai": self.openai_key.text(),
                "anthropic": self.anthropic_key.text(),
            }
        )
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
    