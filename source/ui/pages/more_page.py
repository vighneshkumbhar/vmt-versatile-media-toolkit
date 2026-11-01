"""
more_page.py
"More Tools" panel: Remove Audio, Extract Frame, Media Info.
"""
from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFrame, QStackedWidget, QGroupBox,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal

from ui.styles import COLORS as C


class MorePage(QWidget):
    """Container for less-common operations."""

    settings_changed = Signal()
    extension_open_requested = Signal(str)
    extension_pin_requested = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_tool = "remove_audio"
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # ── Tool selector row ─────────────────────────────────────────
        tool_row = QHBoxLayout()
        tool_row.setSpacing(8)

        self._tool_btns: dict[str, QPushButton] = {}
        tools = [
            ("remove_audio", "🔇  Remove Audio"),
            ("extract_frame", "🖼  Extract Frame"),
            ("media_info",   "ℹ  Media Info"),
        ]
        for tool_id, label in tools:
            btn = QPushButton(label)
            btn.setFixedHeight(36)
            btn.setCheckable(False)
            btn.setStyleSheet(self._inactive_style())
            btn.clicked.connect(lambda checked, t=tool_id: self._switch_tool(t))
            self._tool_btns[tool_id] = btn
            tool_row.addWidget(btn)

        tool_row.addStretch()
        extensions_btn = QPushButton("Extensions")
        extensions_btn.setFixedHeight(36)
        extensions_btn.setStyleSheet(self._inactive_style())
        extensions_btn.clicked.connect(lambda: self._switch_tool("extensions"))
        self._tool_btns["extensions"] = extensions_btn
        tool_row.insertWidget(tool_row.count() - 1, extensions_btn)
        root.addLayout(tool_row)

        # ── Stacked panels ─────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._remove_audio_panel = RemoveAudioPanel()
        self._extract_frame_panel = ExtractFramePanel()
        self._media_info_panel = MediaInfoPanel()
        self._extensions_panel = ExtensionLauncherPanel()
        self._extensions_panel.open_requested.connect(self.extension_open_requested)
        self._extensions_panel.pin_requested.connect(self.extension_pin_requested)

        self._stack.addWidget(self._remove_audio_panel)
        self._stack.addWidget(self._extract_frame_panel)
        self._stack.addWidget(self._media_info_panel)
        self._stack.addWidget(self._extensions_panel)

        root.addWidget(self._stack)

        # Init
        self._switch_tool("remove_audio")

    def _switch_tool(self, tool_id: str) -> None:
        self._active_tool = tool_id
        idx = {"remove_audio": 0, "extract_frame": 1, "media_info": 2, "extensions": 3}
        self._stack.setCurrentIndex(idx.get(tool_id, 0))
        for tid, btn in self._tool_btns.items():
            if tid == tool_id:
                btn.setStyleSheet(self._active_style())
            else:
                btn.setStyleSheet(self._inactive_style())
        self.settings_changed.emit()

    def _active_style(self) -> str:
        return f"""
            QPushButton {{
                background: {C['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 13px;
                font-weight: 600;
            }}
        """

    def _inactive_style(self) -> str:
        return f"""
            QPushButton {{
                background: {C['bg_card']};
                color: {C['text_muted']};
                border: 1px solid {C['border']};
                border-radius: 8px;
                padding: 0 14px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {C['bg_hover']};
                color: {C['text_primary']};
            }}
        """

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def active_tool(self) -> str:
        return self._active_tool

    @property
    def extract_frame_panel(self) -> "ExtractFramePanel":
        return self._extract_frame_panel

    @property
    def media_info_panel(self) -> "MediaInfoPanel":
        return self._media_info_panel

    def register_extension(self, page_id: str, name: str, description: str, pinned: bool) -> None:
        self._extensions_panel.register_extension(page_id, name, description, pinned)

    def unregister_extension(self, page_id: str) -> None:
        self._extensions_panel.unregister_extension(page_id)

    def set_extension_pinned(self, page_id: str, pinned: bool) -> None:
        self._extensions_panel.set_pinned(page_id, pinned)

    def build_ffmpeg_args(self, input_file: str, output_file: str, **kwargs) -> list[str]:
        if self._active_tool == "remove_audio":
            return self._remove_audio_panel.build_ffmpeg_args(input_file, output_file)
        elif self._active_tool == "extract_frame":
            return self._extract_frame_panel.build_ffmpeg_args(input_file, output_file)
        return []

    def get_output_extension(self) -> str:
        if self._active_tool == "remove_audio":
            return self._remove_audio_panel.output_format.lower()
        elif self._active_tool == "extract_frame":
            return self._extract_frame_panel.output_format.lower()
        return "mp4"

    def get_operation_suffix(self) -> str:
        if self._active_tool == "remove_audio":
            return "_noaudio"
        elif self._active_tool == "extract_frame":
            return "_frame"
        return "_output"


class ExtensionLauncherPanel(QWidget):
    """Launcher for enabled extensions; pinning is delegated to MainWindow."""

    open_requested = Signal(str)
    pin_requested = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._extensions: dict[str, dict] = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        heading = QLabel("INSTALLED EXTENSIONS")
        heading.setStyleSheet(f"color: {C['text_dim']}; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent;")
        root.addWidget(heading)
        hint = QLabel("Open any enabled extension here. Pin frequently used extensions to add a shortcut to the sidebar.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {C['text_muted']}; font-size: 13px; background: transparent;")
        root.addWidget(hint)

        self._cards = QVBoxLayout()
        self._cards.setSpacing(10)
        self._cards.addStretch()
        cards = QWidget()
        cards.setLayout(self._cards)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setWidget(cards)
        root.addWidget(scroll, 1)
        self._render()

    def register_extension(self, page_id: str, name: str, description: str, pinned: bool) -> None:
        self._extensions[page_id] = {"name": name, "description": description, "pinned": pinned}
        self._render()

    def unregister_extension(self, page_id: str) -> None:
        self._extensions.pop(page_id, None)
        self._render()

    def set_pinned(self, page_id: str, pinned: bool) -> None:
        if page_id in self._extensions:
            self._extensions[page_id]["pinned"] = pinned
            self._render()

    def _render(self) -> None:
        while self._cards.count() > 1:
            item = self._cards.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self._extensions:
            empty = QLabel("No extensions are enabled. Install or enable one from the Extension Manager.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {C['text_dim']}; background: {C['bg_card']}; border: 1px solid {C['border']}; border-radius: 10px; padding: 24px;")
            self._cards.insertWidget(0, empty)
            return
        for page_id, ext in self._extensions.items():
            card = QFrame()
            card.setStyleSheet(f"background: {C['bg_card']}; border: 1px solid {C['border']}; border-radius: 10px;")
            row = QHBoxLayout(card)
            row.setContentsMargins(16, 14, 16, 14)
            details = QVBoxLayout()
            title = QLabel(ext["name"])
            title.setStyleSheet(f"color: {C['text_primary']}; font-size: 15px; font-weight: 700; background: transparent;")
            desc = QLabel(ext["description"] or "Extension tool")
            desc.setWordWrap(True)
            desc.setStyleSheet(f"color: {C['text_muted']}; font-size: 12px; background: transparent;")
            details.addWidget(title)
            details.addWidget(desc)
            row.addLayout(details, 1)
            open_btn = QPushButton("Open")
            open_btn.clicked.connect(lambda checked=False, p=page_id: self.open_requested.emit(p))
            pin_btn = QPushButton("Unpin" if ext["pinned"] else "Pin")
            pin_btn.clicked.connect(lambda checked=False, p=page_id, value=not ext["pinned"]: self.pin_requested.emit(p, value))
            row.addWidget(open_btn)
            row.addWidget(pin_btn)
            self._cards.insertWidget(self._cards.count() - 1, card)


class RemoveAudioPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card = QFrame()
        card.setProperty("class", "card")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(20, 16, 20, 20)
        card_lay.setSpacing(12)

        title = QLabel("REMOVE AUDIO")
        title.setStyleSheet(f"color: {C['text_dim']}; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent;")

        desc = QLabel(
            "Strips the audio track from your video.\n"
            "The video quality is preserved — no re-encoding is needed."
        )
        desc.setStyleSheet(f"color: {C['text_muted']}; font-size: 13px; background: transparent;")
        desc.setWordWrap(True)

        fmt_row = QHBoxLayout()
        fmt_label = QLabel("Output format:")
        fmt_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        fmt_label.setFixedWidth(110)
        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(["MP4", "MKV", "MOV", "AVI"])
        self._fmt_combo.setMinimumWidth(120)
        fmt_row.addWidget(fmt_label)
        fmt_row.addWidget(self._fmt_combo)
        fmt_row.addStretch()

        fast_note = QLabel("✓  Uses stream copy — process completes almost instantly.")
        fast_note.setStyleSheet(f"color: {C['success']}; font-size: 12px; background: transparent;")

        card_lay.addWidget(title)
        card_lay.addWidget(desc)
        card_lay.addLayout(fmt_row)
        card_lay.addWidget(fast_note)

        layout.addWidget(card)
        layout.addStretch()

    @property
    def output_format(self) -> str:
        return self._fmt_combo.currentText()

    def build_ffmpeg_args(self, input_file: str, output_file: str) -> list[str]:
        # -an removes audio, -c:v copy keeps video stream without re-encoding
        return ["-i", input_file, "-c:v", "copy", "-an", output_file]


class ExtractFramePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card = QFrame()
        card.setProperty("class", "card")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(20, 16, 20, 20)
        card_lay.setSpacing(14)

        title = QLabel("EXTRACT FRAME")
        title.setStyleSheet(f"color: {C['text_dim']}; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent;")
        card_lay.addWidget(title)

        # Timestamp
        ts_row = QHBoxLayout()
        ts_label = QLabel("Timestamp:")
        ts_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        ts_label.setFixedWidth(110)
        self._timestamp_edit = QLineEdit()
        self._timestamp_edit.setPlaceholderText("00:00:00  (leave blank for first frame)")
        self._timestamp_edit.setMinimumWidth(220)
        ts_row.addWidget(ts_label)
        ts_row.addWidget(self._timestamp_edit)
        ts_row.addStretch()

        # Format
        fmt_row = QHBoxLayout()
        fmt_label = QLabel("Save as:")
        fmt_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        fmt_label.setFixedWidth(110)
        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(["PNG", "JPG"])
        self._fmt_combo.setMinimumWidth(100)
        fmt_row.addWidget(fmt_label)
        fmt_row.addWidget(self._fmt_combo)
        fmt_row.addStretch()

        note = QLabel("PNG = lossless quality.  JPG = smaller file.")
        note.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; background: transparent;")

        card_lay.addLayout(ts_row)
        card_lay.addLayout(fmt_row)
        card_lay.addWidget(note)

        layout.addWidget(card)
        layout.addStretch()

    @property
    def timestamp(self) -> str:
        return self._timestamp_edit.text().strip()

    @property
    def output_format(self) -> str:
        return self._fmt_combo.currentText()

    def build_ffmpeg_args(self, input_file: str, output_file: str) -> list[str]:
        args = ["-i", input_file]
        ts = self.timestamp
        if ts:
            args = ["-ss", ts] + args
        fmt = self.output_format.lower()
        if fmt == "jpg":
            args += ["-vframes", "1", "-q:v", "2", output_file]
        else:  # PNG
            args += ["-vframes", "1", output_file]
        return args


class MediaInfoPanel(QWidget):
    """Displays media info for the currently selected file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card = QFrame()
        card.setProperty("class", "card")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(20, 16, 20, 20)
        card_lay.setSpacing(10)

        title = QLabel("MEDIA INFORMATION")
        title.setStyleSheet(f"color: {C['text_dim']}; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent;")
        card_lay.addWidget(title)

        self._info_layout = QVBoxLayout()
        self._info_layout.setSpacing(8)
        self._placeholder = QLabel("Select a file to see its details.")
        self._placeholder.setStyleSheet(f"color: {C['text_dim']}; font-size: 13px; background: transparent;")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._info_layout.addWidget(self._placeholder)
        card_lay.addLayout(self._info_layout)

        layout.addWidget(card)
        layout.addStretch()

    def update_info(self, info) -> None:
        """Update the info panel with a MediaInfo object."""
        # Clear existing
        while self._info_layout.count():
            item = self._info_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if info is None or info.error:
            err_label = QLabel(info.error if info else "No info available.")
            err_label.setStyleSheet(f"color: {C['error']}; font-size: 13px; background: transparent;")
            self._info_layout.addWidget(err_label)
            return

        summary = info.friendly_summary()
        for label, value in summary.items():
            row = QHBoxLayout()
            key_lbl = QLabel(label + ":")
            key_lbl.setStyleSheet(f"color: {C['text_dim']}; font-size: 13px; background: transparent; min-width: 120px;")
            key_lbl.setFixedWidth(130)
            val_lbl = QLabel(value)
            val_lbl.setStyleSheet(f"color: {C['text_primary']}; font-size: 13px; font-weight: 600; background: transparent;")
            row.addWidget(key_lbl)
            row.addWidget(val_lbl)
            row.addStretch()
            self._info_layout.addLayout(row)
