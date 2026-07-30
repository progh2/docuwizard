"""Background worker for essentials report generation (issue #26)."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from docuwizard.services import essentials as essentials_service
from docuwizard.services.essentials import EssentialsError


class EssentialsWorker(QThread):
    status = Signal(str)
    finished_ok = Signal(object)  # EssentialsReport
    failed = Signal(str)

    def __init__(self, project_id: str, parent=None) -> None:
        super().__init__(parent)
        self._project_id = project_id

    def run(self) -> None:  # noqa: D102
        try:
            report = essentials_service.generate_report(
                self._project_id,
                on_status=self.status.emit,
            )
        except (EssentialsError, LookupError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001 — surface unexpected errors to UI
            self.failed.emit(f"예상치 못한 오류: {exc}")
        else:
            self.finished_ok.emit(report)
