"""
audio_page.py
The "Extract Audio" operation panel.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QFrame
)
from PySide6.QtCore import Signal

from core.presets import AUDIO_FORMATS, QUALITY_PRESETS, get_audio_encode_args
from ui.styles import COLORS as C


_FORMAT_INFO = {
    "MP3":  ("libmp3lame", "Universal audio. Plays everywhere."),
    "WAV":  ("pcm_s16le", "Uncompressed. Perfect quality, large files."),
    "FLAC": ("flac",       "Lossless compressed. Perfect quality."),
    "M4A":  ("aac",        "High quality AAC. Great for Apple devices."),
    "OGG":  ("libvorbis",  "Open format. Efficient compression."),
    "AAC":  ("aac",        "Efficient compression, wide compatibility."),
    "OPUS": ("libopus",    "Excellent quality at low bitrates."),
}


class AudioPage(QWidget):
    """Extract or convert audio from video files."""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── Format card ───────────────────────────────────────────────
        fmt_card = QFrame()
        fmt_card.setProperty("class", "card")
        fmt_lay = QVBoxLayout(fmt_card)
        fmt_lay.setContentsMargins(20, 16, 20, 16)
        fmt_lay.setSpacing(12)

        title = QLabel("AUDIO FORMAT")
        title.setStyleSheet(f"color: {C['text_dim']}; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent;")
        fmt_lay.addWidget(title)

        fmt_row = QHBoxLayout()
        fmt_label = QLabel("Save as:")
        fmt_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        fmt_label.setFixedWidth(90)

        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(AUDIO_FORMATS)
        self._fmt_combo.setCurrentText("MP3")
        self._fmt_combo.setMinimumWidth(160)
        self._fmt_combo.currentTextChanged.connect(self._on_format_changed)

        fmt_row.addWidget(fmt_label)
        fmt_row.addWidget(self._fmt_combo)
        fmt_row.addStretch()
        fmt_lay.addLayout(fmt_row)

        self._info_label = QLabel("Universal audio. Plays everywhere.")
        self._info_label.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; background: transparent;")
        fmt_lay.addWidget(self._info_label)

        # ── Quality card ──────────────────────────────────────────────
        q_card = QFrame()
        q_card.setProperty("class", "card")
        q_lay = QHBoxLayout(q_card)
        q_lay.setContentsMargins(20, 14, 20, 14)
        q_lay.setSpacing(12)

        q_label = QLabel("Quality:")
        q_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        q_label.setFixedWidth(90)

        self._quality_combo = QComboBox()
        self._quality_combo.addItems(list(QUALITY_PRESETS.keys()))
        self._quality_combo.setCurrentText("Recommended")
        self._quality_combo.setMinimumWidth(160)

        # Disable quality for lossless formats
        self._quality_combo.currentTextChanged.connect(self.settings_changed)

        q_lay.addWidget(q_label)
        q_lay.addWidget(self._quality_combo)
        q_lay.addStretch()

        # Note
        note = QLabel("ℹ  The video stream will be automatically removed. Only audio is kept.")
        note.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; background: transparent;")
        note.setWordWrap(True)

        layout.addWidget(fmt_card)
        layout.addWidget(q_card)
        layout.addWidget(note)
        layout.addStretch()

    def _on_format_changed(self, fmt: str) -> None:
        _, info = _FORMAT_INFO.get(fmt, ("", ""))
        self._info_label.setText(info)
        # Disable quality for lossless formats
        lossless = fmt in ("WAV", "FLAC")
        self._quality_combo.setEnabled(not lossless)
        self.settings_changed.emit()

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def output_format(self) -> str:
        return self._fmt_combo.currentText()

    @property
    def quality(self) -> str:
        return self._quality_combo.currentText()

    def build_ffmpeg_args(self, input_file: str, output_file: str,
                          **kwargs) -> list[str]:
        codec_args = get_audio_encode_args(self.output_format, self.quality)
        return ["-i", input_file] + codec_args + [output_file]
