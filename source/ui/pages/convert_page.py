"""
convert_page.py
The "Convert" operation panel.
"""
from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QPushButton, QLineEdit, QFileDialog, QFrame, QGroupBox
)
from PySide6.QtCore import Qt, Signal

from core.presets import (
    VIDEO_FORMATS, AUDIO_FORMATS, QUALITY_PRESETS,
    get_video_encode_args, get_audio_encode_args,
    format_to_extension
)
from ui.styles import COLORS as C


class ConvertPage(QWidget):
    """Convert files to a different format."""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── Format group ──────────────────────────────────────────────
        fmt_group = self._make_card()
        fmt_lay = QVBoxLayout(fmt_group)
        fmt_lay.setSpacing(12)

        section_label = self._section_label("Output Format")
        fmt_lay.addWidget(section_label)

        # Format selector row
        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(8)
        type_label = QLabel("Convert to:")
        type_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        type_label.setFixedWidth(90)

        self._fmt_combo = QComboBox()
        all_fmts = VIDEO_FORMATS + ["──────"] + AUDIO_FORMATS
        self._fmt_combo.addItems(all_fmts)
        self._fmt_combo.setMinimumWidth(160)
        self._fmt_combo.currentTextChanged.connect(self._on_format_changed)
        # Disable separator item
        self._fmt_combo.model().item(len(VIDEO_FORMATS)).setEnabled(False)

        fmt_row.addWidget(type_label)
        fmt_row.addWidget(self._fmt_combo)
        fmt_row.addStretch()

        fmt_lay.addLayout(fmt_row)

        # ── Quality group ─────────────────────────────────────────────
        quality_group = self._make_card()
        q_lay = QVBoxLayout(quality_group)
        q_lay.setSpacing(12)
        q_lay.addWidget(self._section_label("Quality"))

        q_row = QHBoxLayout()
        q_row.setSpacing(8)
        q_label = QLabel("Quality:")
        q_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        q_label.setFixedWidth(90)

        self._quality_combo = QComboBox()
        self._quality_combo.addItems(list(QUALITY_PRESETS.keys()))
        self._quality_combo.setCurrentText("Recommended")
        self._quality_combo.setMinimumWidth(160)

        q_row.addWidget(q_label)
        q_row.addWidget(self._quality_combo)
        q_row.addStretch()
        q_lay.addLayout(q_row)

        # ── Info label ────────────────────────────────────────────────
        self._info_label = QLabel()
        self._info_label.setWordWrap(True)
        self._info_label.setStyleSheet(f"""
            color: {C['text_dim']};
            font-size: 11px;
            background: transparent;
        """)
        self._update_info_label("MP4")

        layout.addWidget(fmt_group)
        layout.addWidget(quality_group)
        layout.addWidget(self._info_label)
        layout.addStretch()

    # ── Helpers ────────────────────────────────────────────────────────────

    def _make_card(self) -> QFrame:
        f = QFrame()
        f.setProperty("class", "card")
        f.setContentsMargins(16, 16, 16, 16)
        return f

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(f"""
            color: {C['text_dim']};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
            background: transparent;
        """)
        return lbl

    def _on_format_changed(self, fmt: str) -> None:
        if fmt == "──────":
            return
        self._update_info_label(fmt)
        self.settings_changed.emit()

    def _update_info_label(self, fmt: str) -> None:
        info = {
            "MP4":  "Best compatibility. H.264 video + AAC audio. Plays everywhere.",
            "MKV":  "Flexible container. Supports multiple audio/subtitle tracks.",
            "MOV":  "Apple format. Great for editing workflows.",
            "WebM": "Web-optimised. VP9 video + Opus audio. Smaller files.",
            "AVI":  "Older format. Wide compatibility with legacy players.",
            "MP3":  "Universal audio. Good compression for music.",
            "WAV":  "Uncompressed audio. Lossless quality, large files.",
            "FLAC": "Lossless compressed audio. Perfect quality.",
            "M4A":  "AAC audio in MP4 container. Great for Apple devices.",
            "OGG":  "Open format. Good quality at lower bitrates.",
            "AAC":  "Raw AAC audio. Efficient compression.",
            "OPUS": "Excellent quality at low bitrates. Great for voice.",
        }
        self._info_label.setText(info.get(fmt, ""))

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def output_format(self) -> str:
        fmt = self._fmt_combo.currentText()
        if fmt == "──────":
            return "MP4"
        return fmt

    @property
    def quality(self) -> str:
        return self._quality_combo.currentText()

    def set_format(self, fmt: str) -> None:
        idx = self._fmt_combo.findText(fmt)
        if idx >= 0:
            self._fmt_combo.setCurrentIndex(idx)

    def set_quality(self, q: str) -> None:
        idx = self._quality_combo.findText(q)
        if idx >= 0:
            self._quality_combo.setCurrentIndex(idx)

    def build_ffmpeg_args(self, input_file: str, output_file: str,
                          hw_encoder: str | None = None) -> list[str]:
        fmt = self.output_format
        q = self.quality
        if fmt in AUDIO_FORMATS:
            codec_args = get_audio_encode_args(fmt, q)
        else:
            codec_args = get_video_encode_args(fmt, q, hw_encoder)

        return ["-i", input_file] + codec_args + [output_file]
