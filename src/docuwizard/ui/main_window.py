"""Main application window — project list + file panel (M1)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from docuwizard import __version__
from docuwizard.config import load_settings
from docuwizard.models import Project, ProjectFile
from docuwizard.rag import vectors
from docuwizard.services import files as file_service
from docuwizard.services import projects as project_service
from docuwizard.services.files import FileError
from docuwizard.services.projects import ProjectError
from docuwizard.ui.chat_panel import ChatPanel
from docuwizard.ui.essentials_panel import EssentialsPanel
from docuwizard.ui.favorites_panel import FavoritesPanel
from docuwizard.ui.indexing_worker import IndexingWorker
from docuwizard.ui.settings_dialog import SettingsDialog


class DropFileList(QListWidget):
    """File list that accepts drag-and-drop of local files."""

    def __init__(self, on_paths, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_paths = on_paths
        self.setAcceptDrops(True)
        self.setAlternatingRowColors(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        files = [p for p in paths if p.is_file()]
        if files:
            self._on_paths(files)
            event.acceptProposedAction()
        else:
            event.ignore()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"DocuWizard {__version__}")
        self.resize(1100, 700)
        self._selected_project_id: str | None = None
        self._worker: IndexingWorker | None = None

        self._build_toolbar()
        self._build_body()
        self.refresh_projects()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("메인")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        new_action = QAction("새 프로젝트", self)
        new_action.triggered.connect(self.create_project)
        toolbar.addAction(new_action)

        rename_action = QAction("이름 변경", self)
        rename_action.triggered.connect(self.rename_project)
        toolbar.addAction(rename_action)

        delete_action = QAction("프로젝트 삭제", self)
        delete_action.triggered.connect(self.delete_project)
        toolbar.addAction(delete_action)

        settings_action = QAction("설정", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)

    def _build_body(self) -> None:
        splitter = QSplitter()

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("프로젝트"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("프로젝트 검색…")
        self.search_edit.textChanged.connect(self.refresh_projects)
        left_layout.addWidget(self.search_edit)
        self.project_list = QListWidget()
        self.project_list.currentItemChanged.connect(self._on_project_selected)
        left_layout.addWidget(self.project_list)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.detail_title = QLabel("프로젝트를 선택하세요")
        self.detail_title.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.detail_desc = QLabel("")
        self.detail_desc.setWordWrap(True)
        right_layout.addWidget(self.detail_title)
        right_layout.addWidget(self.detail_desc)

        file_header = QHBoxLayout()
        file_header.addWidget(QLabel("파일"))
        file_header.addStretch(1)
        self.add_files_btn = QPushButton("파일 추가…")
        self.add_files_btn.clicked.connect(self.add_files_dialog)
        self.add_files_btn.setEnabled(False)
        self.index_btn = QPushButton("인덱싱")
        self.index_btn.clicked.connect(self.start_indexing)
        self.index_btn.setEnabled(False)
        self.retry_btn = QPushButton("실패 재시도")
        self.retry_btn.clicked.connect(self.retry_failed_indexing)
        self.retry_btn.setEnabled(False)
        self.reindex_all_btn = QPushButton("전체 재인덱싱")
        self.reindex_all_btn.clicked.connect(self.reindex_all)
        self.reindex_all_btn.setEnabled(False)
        self.reindex_all_btn.setToolTip(
            "모든 파일을 다시 파싱·임베딩합니다. 임베딩 모델을 바꿨을 때 실행하세요."
        )
        self.cancel_index_btn = QPushButton("인덱싱 취소")
        self.cancel_index_btn.clicked.connect(self.cancel_indexing)
        self.cancel_index_btn.setEnabled(False)
        self.delete_file_btn = QPushButton("선택 파일 삭제")
        self.delete_file_btn.clicked.connect(self.delete_selected_file)
        self.delete_file_btn.setEnabled(False)
        file_header.addWidget(self.add_files_btn)
        file_header.addWidget(self.index_btn)
        file_header.addWidget(self.retry_btn)
        file_header.addWidget(self.reindex_all_btn)
        file_header.addWidget(self.cancel_index_btn)
        file_header.addWidget(self.delete_file_btn)
        right_layout.addLayout(file_header)

        self.embed_hint = QLabel("")
        self.embed_hint.setWordWrap(True)
        self.embed_hint.setStyleSheet(
            "color: #8a4b00; background: #fff4e0; padding: 4px; border-radius: 4px;"
        )
        self.embed_hint.setVisible(False)
        right_layout.addWidget(self.embed_hint)

        self.file_list = DropFileList(self.import_paths)
        self.file_list.setEnabled(False)
        right_layout.addWidget(self.file_list)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress_label = QLabel("")
        right_layout.addWidget(self.progress)
        right_layout.addWidget(self.progress_label)

        hint = QLabel(
            "파일을 드래그앤드롭하거나 추가한 뒤 ‘인덱싱’으로 내용을 DB에 저장하세요."
        )
        hint.setStyleSheet("color: #666;")
        right_layout.addWidget(hint)

        files_page = right
        self.chat_panel = ChatPanel()
        self.essentials_panel = EssentialsPanel()
        self.favorites_panel = FavoritesPanel()
        self.favorites_panel.open_conversation.connect(self._open_favorite_conversation)
        self.chat_panel.set_favorites_callback(self.favorites_panel.refresh)
        self.essentials_panel.set_favorites_callback(self.favorites_panel.refresh)

        self.tabs = QTabWidget()
        self.tabs.addTab(files_page, "파일")
        self.tabs.addTab(self.chat_panel, "대화")
        self.tabs.addTab(self.essentials_panel, "필수 포인트")
        self.tabs.addTab(self.favorites_panel, "즐겨찾기")

        splitter.addWidget(left)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)

    def open_settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()

    def refresh_projects(self) -> None:
        query = self.search_edit.text().strip() or None
        current_id = self._selected_project_id
        self.project_list.blockSignals(True)
        self.project_list.clear()
        for project in project_service.list_projects(query):
            item = QListWidgetItem(project.name)
            item.setData(Qt.ItemDataRole.UserRole, project.id)
            item.setToolTip(project.description or project.id)
            self.project_list.addItem(item)
            if project.id == current_id:
                self.project_list.setCurrentItem(item)
        self.project_list.blockSignals(False)
        if self.project_list.currentItem() is None:
            self._clear_detail()
        elif current_id:
            self._load_project_detail(current_id)

    def create_project(self) -> None:
        name, ok = QInputDialog.getText(self, "새 프로젝트", "프로젝트 이름:")
        if not ok or not name.strip():
            return
        description, ok = QInputDialog.getMultiLineText(
            self, "새 프로젝트", "설명 (선택):"
        )
        if not ok:
            return
        try:
            project = project_service.create_project(name, description)
        except ProjectError as exc:
            QMessageBox.warning(self, "오류", str(exc))
            return
        self._selected_project_id = project.id
        self.refresh_projects()

    def rename_project(self) -> None:
        project = self._current_project()
        if project is None:
            QMessageBox.information(self, "안내", "프로젝트를 먼저 선택하세요.")
            return
        name, ok = QInputDialog.getText(
            self, "이름 변경", "프로젝트 이름:", text=project.name
        )
        if not ok or not name.strip():
            return
        description, ok = QInputDialog.getMultiLineText(
            self, "이름 변경", "설명:", text=project.description
        )
        if not ok:
            return
        try:
            project_service.rename_project(project.id, name, description)
        except ProjectError as exc:
            QMessageBox.warning(self, "오류", str(exc))
            return
        self.refresh_projects()

    def delete_project(self) -> None:
        project = self._current_project()
        if project is None:
            QMessageBox.information(self, "안내", "프로젝트를 먼저 선택하세요.")
            return
        answer = QMessageBox.question(
            self,
            "프로젝트 삭제",
            (
                f"‘{project.name}’ 프로젝트와 포함된 파일을 모두 삭제할까요?\n"
                "이 작업은 되돌릴 수 없습니다."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            project_service.delete_project(project.id)
        except ProjectError as exc:
            QMessageBox.warning(self, "오류", str(exc))
            return
        self._selected_project_id = None
        self.refresh_projects()

    def add_files_dialog(self) -> None:
        if not self._selected_project_id:
            return
        paths, _ = QFileDialog.getOpenFileNames(self, "프로젝트에 파일 추가")
        if paths:
            self.import_paths([Path(p) for p in paths])

    def import_paths(self, paths: list[Path]) -> None:
        if not self._selected_project_id:
            return
        try:
            added = file_service.add_files(self._selected_project_id, paths)
        except (FileError, ProjectError, OSError) as exc:
            QMessageBox.warning(self, "파일 추가 실패", str(exc))
            return
        skipped = len(paths) - len(added)
        if skipped > 0:
            QMessageBox.information(
                self,
                "중복 파일 건너뜀",
                f"{skipped}개 파일은 동일한 내용이 이미 프로젝트에 있어 건너뛰었습니다.",
            )
        self._load_project_detail(self._selected_project_id)

    def delete_selected_file(self) -> None:
        if not self._selected_project_id:
            return
        item = self.file_list.currentItem()
        if item is None:
            return
        file_id = item.data(Qt.ItemDataRole.UserRole)
        name = item.text()
        answer = QMessageBox.question(
            self,
            "파일 삭제",
            f"‘{name}’ 파일을 삭제할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            file_service.delete_file(self._selected_project_id, file_id)
        except (FileError, ProjectError) as exc:
            QMessageBox.warning(self, "오류", str(exc))
            return
        self._load_project_detail(self._selected_project_id)

    def start_indexing(self) -> None:
        self._start_worker(only_failed_or_pending=True)

    def retry_failed_indexing(self) -> None:
        self._start_worker(only_failed_or_pending=True)

    def reindex_all(self) -> None:
        answer = QMessageBox.question(
            self,
            "전체 재인덱싱",
            "모든 파일을 다시 파싱하고 임베딩합니다. 파일이 많으면 오래 걸릴 수 있습니다.\n"
            "계속할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._start_worker(only_failed_or_pending=False)

    def cancel_indexing(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self.progress_label.setText("취소 요청됨…")

    def _start_worker(self, *, only_failed_or_pending: bool) -> None:
        if not self._selected_project_id:
            return
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "안내", "이미 인덱싱이 진행 중입니다.")
            return
        self._worker = IndexingWorker(
            self._selected_project_id,
            only_failed_or_pending=only_failed_or_pending,
            parent=self,
        )
        self._worker.progress.connect(self._on_index_progress)
        self._worker.finished_ok.connect(self._on_index_finished)
        self._worker.failed.connect(self._on_index_failed)
        self._set_indexing_ui(True)
        self.progress.setValue(0)
        self.progress_label.setText("인덱싱 시작…")
        self._worker.start()

    def _on_index_progress(self, current: int, total: int, name: str, state: str) -> None:
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(current)
        self.progress_label.setText(f"[{current}/{total}] {name} — {state}")
        if self._selected_project_id:
            self._load_project_detail(self._selected_project_id)

    def _on_index_finished(self, ok: int, failed: int) -> None:
        self._set_indexing_ui(False)
        self.progress_label.setText(f"완료 — 성공 {ok}, 실패 {failed}")
        if self._selected_project_id:
            self._load_project_detail(self._selected_project_id)

    def _on_index_failed(self, message: str) -> None:
        self._set_indexing_ui(False)
        self.progress_label.setText("인덱싱 오류")
        QMessageBox.warning(self, "인덱싱 실패", message)
        if self._selected_project_id:
            self._load_project_detail(self._selected_project_id)

    def _set_indexing_ui(self, running: bool) -> None:
        enabled = bool(self._selected_project_id) and not running
        self.index_btn.setEnabled(enabled)
        self.retry_btn.setEnabled(enabled)
        self.reindex_all_btn.setEnabled(enabled)
        self.cancel_index_btn.setEnabled(running)
        self.add_files_btn.setEnabled(enabled)
        self.delete_file_btn.setEnabled(enabled)

    def _on_project_selected(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if current is None:
            self._clear_detail()
            return
        project_id = current.data(Qt.ItemDataRole.UserRole)
        self._selected_project_id = project_id
        self._load_project_detail(project_id)

    def _load_project_detail(self, project_id: str) -> None:
        try:
            project = project_service.get_project(project_id)
            files = file_service.list_files(project_id)
        except ProjectError:
            self._clear_detail()
            return
        self.detail_title.setText(project.name)
        self.detail_desc.setText(project.description or "(설명 없음)")
        self.chat_panel.set_project(project_id)
        self.essentials_panel.set_project(project_id)
        self.favorites_panel.set_project(project_id)
        running = bool(self._worker and self._worker.isRunning())
        self.add_files_btn.setEnabled(not running)
        self.delete_file_btn.setEnabled(not running)
        self.index_btn.setEnabled(not running)
        self.retry_btn.setEnabled(not running)
        self.reindex_all_btn.setEnabled(not running)
        self.cancel_index_btn.setEnabled(running)
        self.file_list.setEnabled(True)
        self.file_list.clear()
        for file in files:
            self.file_list.addItem(self._file_item(file))
        self._update_embed_hint(project_id)

    def _update_embed_hint(self, project_id: str) -> None:
        embed_model = str(
            load_settings().get("llm", {}).get("ollama_embed_model", "")
        )
        try:
            stale = vectors.count_stale_embeddings(project_id, embed_model)
        except Exception:  # noqa: BLE001 — hint only, never block the UI
            stale = 0
        if stale > 0:
            self.embed_hint.setText(
                f"⚠ 임베딩 모델이 변경되었습니다. 문서 조각 {stale}개가 이전 모델"
                f"(현재: {embed_model})로 색인되어 검색에서 제외됩니다. "
                "‘전체 재인덱싱’을 실행하세요."
            )
            self.embed_hint.setVisible(True)
        else:
            self.embed_hint.setVisible(False)

    def _file_item(self, file: ProjectFile) -> QListWidgetItem:
        size_kb = max(file.size / 1024, 0.1)
        status = str(file.status)
        if file.error:
            status = f"{status} ({file.error})"
        text = f"{file.original_name}  ·  {size_kb:.1f} KB  ·  {status}"
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, file.id)
        item.setToolTip(file.stored_name)
        return item

    def _clear_detail(self) -> None:
        self._selected_project_id = None
        self.chat_panel.set_project(None)
        self.essentials_panel.set_project(None)
        self.favorites_panel.set_project(None)
        self.detail_title.setText("프로젝트를 선택하세요")
        self.detail_desc.setText("")
        self.file_list.clear()
        self.file_list.setEnabled(False)
        self.add_files_btn.setEnabled(False)
        self.delete_file_btn.setEnabled(False)
        self.index_btn.setEnabled(False)
        self.retry_btn.setEnabled(False)
        self.reindex_all_btn.setEnabled(False)
        self.cancel_index_btn.setEnabled(False)
        self.embed_hint.setVisible(False)

    def _open_favorite_conversation(self, conversation_id: str) -> None:
        self.tabs.setCurrentWidget(self.chat_panel)
        self.chat_panel.open_conversation(conversation_id)

    def _current_project(self) -> Project | None:
        if not self._selected_project_id:
            return None
        try:
            return project_service.get_project(self._selected_project_id)
        except ProjectError:
            return None
