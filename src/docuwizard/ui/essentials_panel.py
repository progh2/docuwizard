"""Essential points report panel (issues #25–#27)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from docuwizard.rag.prompt import format_location
from docuwizard.services import conversations as conversation_service
from docuwizard.services import essentials as essentials_service
from docuwizard.ui.essentials_worker import EssentialsWorker


class EssentialsPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._project_id: str | None = None
        self._worker: EssentialsWorker | None = None
        self._favorites_callback = None

        layout = QVBoxLayout(self)

        top_row = QHBoxLayout()
        title = QLabel("필수 포인트")
        title.setObjectName("sectionTitle")
        top_row.addWidget(title)
        top_row.addStretch(1)
        self.generate_btn = QPushButton("리포트 생성")
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.clicked.connect(self.generate_report)
        top_row.addWidget(self.generate_btn)
        self.version_combo = QComboBox()
        self.version_combo.currentIndexChanged.connect(self._on_version_changed)
        top_row.addWidget(self.version_combo, stretch=1)
        self.star_report_btn = QPushButton("★ 리포트")
        self.star_report_btn.clicked.connect(self.toggle_report_star)
        top_row.addWidget(self.star_report_btn)
        self.star_item_btn = QPushButton("★ 선택 항목")
        self.star_item_btn.clicked.connect(self.toggle_item_star)
        top_row.addWidget(self.star_item_btn)
        layout.addLayout(top_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")
        layout.addWidget(self.status_label)

        self.list = QListWidget()
        self.list.setWordWrap(True)
        self.list.setAlternatingRowColors(True)
        layout.addWidget(self.list)

        hint = QLabel(
            "문서에서 일정·제출물·자격·평가·의무·리스크 등 꼭 알아야 할 항목을 "
            "요약합니다. 항목을 선택해 ★로 즐겨찾기할 수 있습니다."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.set_project(None)

    def set_favorites_callback(self, callback) -> None:
        self._favorites_callback = callback

    def set_project(self, project_id: str | None) -> None:
        self._project_id = project_id
        self.refresh_versions()

    def refresh_versions(self, *, select_report_id: str | None = None) -> None:
        self.version_combo.blockSignals(True)
        self.version_combo.clear()
        reports = (
            essentials_service.list_reports(self._project_id)
            if self._project_id
            else []
        )
        for report in reports:
            star = "★ " if report.is_starred else ""
            label = f"{star}v{report.version} · {report.created_at[:16]} · {report.model}"
            self.version_combo.addItem(label, report.id)
        self.version_combo.blockSignals(False)

        has_project = bool(self._project_id)
        running = bool(self._worker and self._worker.isRunning())
        self.generate_btn.setEnabled(has_project and not running)
        has_report = self.version_combo.count() > 0
        self.version_combo.setEnabled(has_report)
        self.star_report_btn.setEnabled(has_report)
        self.star_item_btn.setEnabled(has_report)

        if select_report_id is not None:
            index = self.version_combo.findData(select_report_id)
            if index >= 0:
                self.version_combo.setCurrentIndex(index)
        self._load_current_report()

    def _on_version_changed(self, _index: int) -> None:
        self._load_current_report()

    def _load_current_report(self) -> None:
        self.list.clear()
        report_id = self.version_combo.currentData()
        if not report_id:
            if self._project_id:
                self.list.addItem(
                    QListWidgetItem("리포트가 없습니다. ‘리포트 생성’을 누르세요.")
                )
            else:
                self.list.addItem(QListWidgetItem("프로젝트를 선택하세요"))
            return
        try:
            report = essentials_service.get_report(report_id)
        except LookupError:
            return
        last_category = None
        for item in report.items:
            if item.category != last_category:
                header = QListWidgetItem(f"— {item.category_name} —")
                header.setFlags(Qt.ItemFlag.NoItemFlags)
                self.list.addItem(header)
                last_category = item.category
            star = "★ " if item.is_starred else ""
            widget_item = QListWidgetItem(f"{star}{item.summary}")
            widget_item.setData(Qt.ItemDataRole.UserRole, item.id)
            widget_item.setToolTip(self._citation_tooltip(item.citation_ids))
            self.list.addItem(widget_item)

    def _citation_tooltip(self, citation_ids: list[str]) -> str:
        chunks = conversation_service.get_chunks_by_ids(citation_ids)
        if not chunks:
            return "(근거 없음)"
        lines = [f"근거: {format_location(chunk)}" for chunk in chunks]
        return "\n".join(lines)

    def generate_report(self) -> None:
        if not self._project_id:
            return
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "안내", "이미 리포트를 생성 중입니다.")
            return
        self._worker = EssentialsWorker(self._project_id, parent=self)
        self._worker.status.connect(self.status_label.setText)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self.generate_btn.setEnabled(False)
        self.status_label.setText("리포트 생성 시작…")
        self._worker.start()

    def _on_finished(self, report) -> None:
        self.generate_btn.setEnabled(True)
        self.refresh_versions(select_report_id=report.id)

    def _on_failed(self, message: str) -> None:
        self.generate_btn.setEnabled(True)
        self.status_label.setText("실패")
        QMessageBox.warning(self, "리포트 생성 실패", message)

    def toggle_report_star(self) -> None:
        report_id = self.version_combo.currentData()
        if not report_id:
            return
        essentials_service.toggle_report_star(report_id)
        self.refresh_versions(select_report_id=report_id)
        self._notify_favorites()

    def toggle_item_star(self) -> None:
        current = self.list.currentItem()
        if current is None:
            return
        item_id = current.data(Qt.ItemDataRole.UserRole)
        if not item_id:
            return
        essentials_service.toggle_item_star(str(item_id))
        row = self.list.currentRow()
        self._load_current_report()
        self.list.setCurrentRow(row)
        self._notify_favorites()

    def _notify_favorites(self) -> None:
        if self._favorites_callback:
            self._favorites_callback()
