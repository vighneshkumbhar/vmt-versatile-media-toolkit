"""
gif_page.py
The "Create GIF" operation panel.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QLineEdit, QFrame
)
from PySide6.QtCore import Signal

from core.presets import GIF_FPS_PRESETS, get_gif_args
from ui.styles import COLORS as C


class GifPage(QWidget):
    """Create an animated GIF from a video."""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── GIF settings card ─────────────────────────────────────────
        card = QFrame()
        card.setProperty("class", "card")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(20, 16, 20, 20)
        card_lay.setSpacing(14)

        title = QLabel("GIF SETTINGS")
        title.setStyleSheet(f"color: {C['text_dim']}; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent;")
        card_lay.addWidget(title)

        # FPS
        fps_row = self._row("Frame rate:")
        self._fps_combo = QComboBox()
        self._fps_combo.addItems(GIF_FPS_PRESETS)
        self._fps_combo.setCurrentText("15")
        self._fps_combo.setMinimumWidth(100)
        self._add_widget_to_row(fps_row, self._fps_combo,
                                 "Lower FPS = smaller file. 10–15 is usually good.")

        # Width
        width_row = self._row("Width (px):")
        self._width_spin = QSpinBox()
        self._width_spin.setRange(64, 1920)
        self._width_spin.setValue(480)
        self._width_spin.setSingleStep(16)
        self._width_spin.setFixedWidth(100)
        self._add_widget_to_row(width_row, self._width_spin,
                                 "Height is calculated automatically to keep ratio.")

        # Start time
        start_row = self._row("Start time:")
        self._start_edit = QLineEdit()
        self._start_edit.setPlaceholderText("00:00:00  (optional)")
        self._start_edit.setFixedWidth(180)
        self._add_widget_to_row(start_row, self._start_edit,
                                 "Leave blank to start from beginning.")

        # Duration
        dur_row = self._row("Duration:")
        self._dur_edit = QLineEdit()
        self._dur_edit.setPlaceholderText("00:00:05  (optional)")
        self._dur_edit.setFixedWidth(180)
        self._add_widget_to_row(dur_row, self._dur_edit,
                                 "Leave blank to use the whole video.")

        card_lay.addLayout(fps_row)
        card_lay.addLayout(width_row)
        card_lay.addLayout(start_row)
        card_lay.addLayout(dur_row)

        # Warning
        warn_card = QFrame()
        warn_card.setStyleSheet(f"""
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 8px;
        """)
        warn_lay = QHBoxLayout(warn_card)
        warn_lay.setContentsMargins(14, 10, 14, 10)
        warn_icon = QLabel("⚠")
        warn_icon.setStyleSheet(f"color: {C['warning']}; font-size: 16px; background: transparent;")
        warn_text = QLabel(
            "GIFs are uncompressed — they can be surprisingly large. "
            "Keep the duration short (under 10 seconds) and width small for web use."
        )
        warn_text.setWordWrap(True)
        warn_text.setStyleSheet(f"color: {C['warning']}; font-size: 12px; background: transparent;")
        warn_lay.addWidget(warn_icon)
        warn_lay.addWidget(warn_text)

        layout.addWidget(card)
        layout.addWidget(warn_card)
        layout.addStretch()

    def _row(self, label_text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        lbl.setFixedWidth(90)
        row.addWidget(lbl)
        return row

    def _add_widget_to_row(self, row: QHBoxLayout, widget, hint: str = "") -> None:
        row.addWidget(widget)
        if hint:
            hint_label = QLabel(hint)
            hint_label.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; background: transparent;")
            row.addWidget(hint_label)
        row.addStretch()

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def fps(self) -> int:
        try:
            return int(self._fps_combo.currentText())
        except ValueError:
            return 15

    @property
    def width(self) -> int:
        return self._width_spin.value()

    @property
    def start_time(self) -> str:
        return self._start_edit.text().strip()

    @property
    def duration(self) -> str:
        return self._dur_edit.text().strip()

    def build_ffmpeg_args(self, input_file: str, output_file: str, **kwargs) -> list[str]:
        gif_args = get_gif_args(self.fps, self.width, self.start_time, self.duration)
        return ["-i", input_file] + gif_args + [output_file]
