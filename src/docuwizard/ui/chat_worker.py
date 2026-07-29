"""Background chat worker for RAG answers."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from docuwizard.rag.orchestrator import RagError, answer_question


class ChatWorker(QThread):
    token = Signal(str)
    finished_ok = Signal(object)  # RagAnswer
    failed = Signal(str)

    def __init__(self, project_id: str, question: str, parent=None) -> None:
        super().__init__(parent)
        self.project_id = project_id
        self.question = question

    def run(self) -> None:
        try:
            answer = answer_question(
                self.project_id,
                self.question,
                stream=True,
                on_token=lambda t: self.token.emit(t),
            )
            self.finished_ok.emit(answer)
        except RagError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
