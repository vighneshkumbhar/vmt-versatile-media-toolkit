"""
file_list.py
Displays added files with media info, selection, and removal controls.
"""
from __future__ import annotations
import os
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont

from core.ffprobe_info import probe, MediaInfo
from utils.file_utils import human_size, is_supported_media
from ui.styles import COLORS as C


class FileItemWidget(QFrame):
    """One row in the file list."""

    remove_requested = Signal(str)  # file path
    selected = Signal(str)          # file path

    _STATUS_COLORS = {
        "ok":      C['success'],
        "error":   C['error'],
        "loading": C['text_dim'],
    }

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self._info: Optional[MediaInfo] = None
        self.setProperty("class", "card-alt")
        self.setCursor(Qt.PointingHandCursor)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # File type icon
        ext = os.path.splitext(self.file_path)[1].lstrip(".").upper()
        self._icon = QLabel(ext[:4] if ext else "?")
        self._icon.setFixedSize(44, 44)
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setStyleSheet(f"""
            background-color: {C['bg_card']};
            color: {C['accent_light']};
            border-radius: 8px;
            font-size: 11px;
            font-weight: 700;
        """)

        # Name + info column
        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        self._name_label = QLabel(os.path.basename(self.file_path))
        self._name_label.setStyleSheet(f"""
            color: {C['text_primary']};
            font-size: 13px;
            font-weight: 600;
            background: transparent;
        """)
        self._name_label.setMaximumWidth(400)
        self._name_label.setToolTip(self.file_path)

        self._meta_label = QLabel("Analysing…")
        self._meta_label.setStyleSheet(f"""
            color: {C['text_dim']};
            font-size: 11px;
            background: transparent;
        """)

        info_col.addWidget(self._name_label)
        info_col.addWidget(self._meta_label)

        # Status dot
        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet(f"color: {C['text_dim']}; background: transparent;")
        self._status_dot.setAlignment(Qt.AlignCenter)
        self._status_dot.setFixedWidth(20)

        # Remove button
        self._remove_btn = QPushButton("✕")
        self._remove_btn.setProperty("class", "ghost")
        self._remove_btn.setFixedSize(28, 28)
        self._remove_btn.setToolTip("Remove from list")
        self._remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.file_path))

        layout.addWidget(self._icon)
        layout.addLayout(info_col)
        layout.addStretch()
        layout.addWidget(self._status_dot)
        layout.addWidget(self._remove_btn)

    def set_info(self, info: MediaInfo) -> None:
        self._info = info
        if info.error:
            self._meta_label.setText(f"⚠ {info.error[:80]}")
            self._meta_label.setStyleSheet(f"color: {C['error']}; font-size: 11px; background: transparent;")
            self._status_dot.setStyleSheet(f"color: {C['error']}; background: transparent;")
        else:
            parts = []
            if info.primary_video:
                v = info.primary_video
                if v.width and v.height:
                    parts.append(f"{v.width}×{v.height}")
                if v.fps > 0:
                    parts.append(f"{v.fps:.0f}fps")
            if info.primary_audio:
                a = info.primary_audio
                parts.append(a.codec_name.upper() if a.codec_name else "Audio")
            parts.append(info.duration_hms)
            parts.append(info.file_size_human)
            self._meta_label.setText("  •  ".join(parts))
            self._meta_label.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; background: transparent;")
            self._status_dot.setStyleSheet(f"color: {C['success']}; background: transparent;")

    def mousePressEvent(self, event) -> None:
        self.selected.emit(self.file_path)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        if selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {C['bg_hover']};
                    border-radius: 10px;
                    border: 1px solid {C['accent']};
                }}
            """)
        else:
            self.setStyleSheet("")


class FileList(QWidget):
    """
    Scrollable list of added files. Runs ffprobe in background for media info.
    """

    files_changed = Signal()            # any add/remove
    file_selected = Signal(str)         # file path
    media_info_ready = Signal(str, object)  # path, MediaInfo

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: list[str] = []           # ordered list of paths
        self._items: dict[str, FileItemWidget] = {}
        self._selected: Optional[str] = None
        self._ffprobe_path: str = ""
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 8)

        self._count_label = QLabel("No files added")
        self._count_label.setStyleSheet(f"""
            color: {C['text_muted']};
            font-size: 12px;
            font-weight: 500;
            background: transparent;
        """)

        self._clear_btn = QPushButton("Clear all")
        self._clear_btn.setProperty("class", "ghost")
        self._clear_btn.setFixedHeight(24)
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {C['error']};
                font-size: 11px;
                padding: 0 6px;
            }}
            QPushButton:hover {{ text-decoration: underline; }}
        """)
        self._clear_btn.clicked.connect(self.clear_all)
        self._clear_btn.hide()

        header.addWidget(self._count_label)
        header.addStretch()
        header.addWidget(self._clear_btn)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.NoFrame)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._list_container)

        layout.addLayout(header)
        layout.addWidget(self._scroll)

    def set_ffprobe_path(self, path: str) -> None:
        self._ffprobe_path = path

    def add_files(self, paths: list[str]) -> None:
        new_paths = []
        for p in paths:
            if p not in self._files:
                self._files.append(p)
                new_paths.append(p)

        for p in new_paths:
            item = FileItemWidget(p)
            item.remove_requested.connect(self.remove_file)
            item.selected.connect(self._on_item_selected)
            # Insert before the stretch
            self._list_layout.insertWidget(
                self._list_layout.count() - 1, item)
            self._items[p] = item

        self._update_count()
        if new_paths:
            self.files_changed.emit()
            # Probe in background
            self._probe_files(new_paths)

    def remove_file(self, path: str) -> None:
        if path in self._files:
            self._files.remove(path)
        if path in self._items:
            w = self._items.pop(path)
            self._list_layout.removeWidget(w)
            w.deleteLater()
        if self._selected == path:
            self._selected = None
        self._update_count()
        self.files_changed.emit()

    def clear_all(self) -> None:
        for path in list(self._files):
            self.remove_file(path)

    @property
    def file_paths(self) -> list[str]:
        return list(self._files)

    @property
    def selected_file(self) -> Optional[str]:
        return self._selected

    @property
    def count(self) -> int:
        return len(self._files)

    def _on_item_selected(self, path: str) -> None:
        if self._selected and self._selected in self._items:
            self._items[self._selected].set_selected(False)
        self._selected = path
        if path in self._items:
            self._items[path].set_selected(True)
        self.file_selected.emit(path)

    def _update_count(self) -> None:
        n = len(self._files)
        if n == 0:
            self._count_label.setText("No files added")
            self._clear_btn.hide()
        elif n == 1:
            self._count_label.setText("1 file")
            self._clear_btn.show()
        else:
            self._count_label.setText(f"{n} files")
            self._clear_btn.show()

    def _probe_files(self, paths: list[str]) -> None:
        """Probe each file in a background thread."""
        if not self._ffprobe_path:
            return
        thread = _ProbeThread(paths, self._ffprobe_path, self)
        thread.result_ready.connect(self._on_probe_result)
        thread.start()
        # Keep reference
        if not hasattr(self, "_probe_threads"):
            self._probe_threads = []
        self._probe_threads.append(thread)

    def _on_probe_result(self, path: str, info: object) -> None:
        if path in self._items:
            self._items[path].set_info(info)
        self.media_info_ready.emit(path, info)


class _ProbeThread(QThread):
    """Background thread that probes a list of files with ffprobe."""
    result_ready = Signal(str, object)

    def __init__(self, paths: list[str], ffprobe_path: str, parent=None):
        super().__init__(parent)
        self._paths = paths
        self._ffprobe_path = ffprobe_path

    def run(self) -> None:
        for path in self._paths:
            info = probe(self._ffprobe_path, path)
            self.result_ready.emit(path, info)
