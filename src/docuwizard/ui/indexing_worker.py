"""Background indexing worker for the GUI (issue #14)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from docuwizard.ingest.pipeline import index_project_files


class IndexingWorker(QThread):
    progress = Signal(int, int, str, str)  # current, total, filename, state
    finished_ok = Signal(int, int)  # success, failed
    failed = Signal(str)

    def __init__(
        self,
        project_id: str,
        *,
        only_failed_or_pending: bool = True,
        db: Path | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.project_id = project_id
        self.only_failed_or_pending = only_failed_or_pending
        self.db = db
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            ok, failed = index_project_files(
                self.project_id,
                only_failed_or_pending=self.only_failed_or_pending,
                db=self.db,
                cancel_check=lambda: self._cancel,
                on_progress=lambda cur, total, name, state: self.progress.emit(
                    cur, total, name, state
                ),
            )
            self.finished_ok.emit(ok, failed)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
