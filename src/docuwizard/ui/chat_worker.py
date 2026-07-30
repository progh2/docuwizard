"""Background chat worker for RAG answers (cancellable, multi-turn)."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from docuwizard.config import load_settings
from docuwizard.llm.factory import create_chat_client
from docuwizard.llm.ollama import OllamaClient, OllamaConfig
from docuwizard.rag.orchestrator import RagCancelled, RagError, answer_question


class ChatWorker(QThread):
    token = Signal(str)
    status = Signal(str)
    finished_ok = Signal(object)  # RagAnswer
    cancelled = Signal(str)  # partial answer text
    failed = Signal(str)

    def __init__(
        self,
        project_id: str,
        question: str,
        *,
        history: list[dict[str, str]] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.project_id = project_id
        self.question = question
        self.history = history or []
        self._cancel_requested = False
        settings = load_settings()
        self._embedder = OllamaClient(OllamaConfig.from_settings(settings))
        self._chat_client = create_chat_client(settings, embedder=self._embedder)

    def cancel(self) -> None:
        """Request cancellation; also unblocks a pending stream read."""
        self._cancel_requested = True
        self._chat_client.abort()

    def run(self) -> None:
        try:
            answer = answer_question(
                self.project_id,
                self.question,
                client=self._embedder,
                chat_client=self._chat_client,
                stream=True,
                history=self.history,
                on_token=lambda t: self.token.emit(t),
                on_status=lambda s: self.status.emit(s),
                cancel_check=lambda: self._cancel_requested,
            )
            self.finished_ok.emit(answer)
        except RagCancelled as exc:
            self.cancelled.emit(exc.partial)
        except RagError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
