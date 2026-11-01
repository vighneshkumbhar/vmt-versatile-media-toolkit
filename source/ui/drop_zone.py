"""
drop_zone.py
Drag-and-drop + click-to-browse file import widget.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Callable, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QFileDialog, QFrame
)
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QPen, QColor

from utils.file_utils import is_supported_media
from ui.styles import COLORS as C


class DropZone(QWidget):
    """
    A widget that accepts drag-and-drop of files/folders
    and provides file picker buttons.
    Emits files_dropped(list[str]) when files are added.
    """

    files_dropped = Signal(list)  # list of file paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_active = False
        self.setAcceptDrops(True)
        self.setMinimumHeight(140)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignCenter)

        # Icon + main text
        icon_label = QLabel("⬇")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(f"""
            font-size: 32px;
            color: {C['accent']};
            background: transparent;
        """)

        self._main_label = QLabel("Drop files here")
        self._main_label.setAlignment(Qt.AlignCenter)
        self._main_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {C['text_primary']};
            background: transparent;
        """)

        sub_label = QLabel("Videos, audio, or folders — any format FFmpeg supports")
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setStyleSheet(f"""
            font-size: 12px;
            color: {C['text_muted']};
            background: transparent;
        """)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.setAlignment(Qt.AlignCenter)

        add_files_btn = QPushButton("  Add Files")
        add_files_btn.setProperty("class", "primary")
        add_files_btn.setFixedHeight(36)
        add_files_btn.setMinimumWidth(120)
        add_files_btn.clicked.connect(self._browse_files)

        add_folder_btn = QPushButton("  Add Folder")
        add_folder_btn.setFixedHeight(36)
        add_folder_btn.setMinimumWidth(120)
        add_folder_btn.clicked.connect(self._browse_folder)

        btn_row.addWidget(add_files_btn)
        btn_row.addWidget(add_folder_btn)

        layout.addWidget(icon_label)
        layout.addWidget(self._main_label)
        layout.addWidget(sub_label)
        layout.addSpacing(8)
        layout.addLayout(btn_row)

    # ── Drag & Drop ────────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            self._drag_active = True
            self.update()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self._drag_active = False
        self.update()

    def dropEvent(self, event: QDropEvent) -> None:
        self._drag_active = False
        self.update()
        urls = event.mimeData().urls()
        paths = []
        for url in urls:
            local = url.toLocalFile()
            if os.path.isdir(local):
                paths.extend(self._collect_from_folder(local))
            elif os.path.isfile(local):
                paths.append(local)
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._drag_active:
            color = QColor(C['accent'])
            bg = QColor(C['accent'])
            bg.setAlpha(25)
            painter.fillRect(self.rect(), bg)
        else:
            color = QColor(C['border'])

        pen = QPen(color)
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        r = self.rect().adjusted(2, 2, -2, -2)
        painter.drawRoundedRect(r, 8, 8)

    # ── File pickers ───────────────────────────────────────────────────────────

    def _browse_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Media Files",
            "",
            "Media Files (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.wmv *.mpeg *.mpg "
            "*.m4v *.ts *.m2ts *.3gp *.mp3 *.wav *.flac *.aac *.m4a *.ogg *.opus "
            "*.wma *.aiff *.gif);;"
            "All Files (*.*)"
        )
        if paths:
            self.files_dropped.emit(paths)

    def _browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            paths = self._collect_from_folder(folder)
            if paths:
                self.files_dropped.emit(paths)

    @staticmethod
    def _collect_from_folder(folder: str) -> list[str]:
        result = []
        for root, _, files in os.walk(folder):
            for f in sorted(files):
                p = os.path.join(root, f)
                if is_supported_media(p):
                    result.append(p)
        return result
