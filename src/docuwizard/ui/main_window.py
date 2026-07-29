"""Main application window (stub shell for M0/M1)."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from docuwizard import __version__
from docuwizard.paths import data_dir


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"DocuWizard {__version__}")
        self.resize(960, 640)

        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("DocuWizard")
        title.setStyleSheet("font-size: 28px; font-weight: 600;")
        subtitle = QLabel(
            "로컬 문서 기반 RAG 질의응답 앱입니다.\n"
            f"데이터 경로: {data_dir()}\n"
            "프로젝트·파일·채팅 UI는 이후 이슈에서 구현됩니다."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        self.setCentralWidget(root)
