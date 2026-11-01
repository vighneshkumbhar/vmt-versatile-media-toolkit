"""
compress_page.py
The "Compress" operation panel.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton,
    QButtonGroup, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from core.presets import QUALITY_PRESETS, get_video_encode_args
from ui.styles import COLORS as C


_COMPRESS_PRESETS = [
    ("Best quality",   "Best Quality",  "Largest file, no quality loss"),
    ("High quality",   "High Quality",  "Very good quality, moderate reduction"),
    ("Recommended",    "Recommended",   "Great balance of quality and size"),
    ("Smaller file",   "Smaller File",  "Noticeable reduction, acceptable quality"),
    ("Smallest file",  "Smallest File", "Maximum compression, quality loss likely"),
]


class CompressPage(QWidget):
    """Compress video with simple quality radio buttons."""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── Card ──────────────────────────────────────────────────────
        card = QFrame()
        card.setProperty("class", "card")
        card_lay = QVBoxLayout(card)
        card_lay.setSpacing(8)
        card_lay.setContentsMargins(20, 16, 20, 16)

        title_row = QHBoxLayout()
        title = QLabel("COMPRESSION LEVEL")
        title.setStyleSheet(f"""
            color: {C['text_dim']};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
            background: transparent;
        """)
        title_row.addWidget(title)
        title_row.addStretch()
        card_lay.addLayout(title_row)
        card_lay.addSpacing(4)

        self._btn_group = QButtonGroup(self)
        self._presets: list[tuple[QRadioButton, str]] = []

        for i, (label, preset_key, desc) in enumerate(_COMPRESS_PRESETS):
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background: {C['bg_card_alt']};
                    border-radius: 8px;
                    border: 1px solid {C['border']};
                }}
                QFrame:hover {{
                    border-color: {C['accent']};
                }}
            """)
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(14, 10, 14, 10)
            row_lay.setSpacing(12)

            rb = QRadioButton(label)
            rb.setStyleSheet(f"""
                QRadioButton {{
                    color: {C['text_primary']};
                    font-size: 13px;
                    font-weight: 500;
                    background: transparent;
                    spacing: 10px;
                }}
                QRadioButton::indicator {{
                    width: 18px;
                    height: 18px;
                    border-radius: 9px;
                    border: 2px solid {C['border']};
                    background: {C['bg_input']};
                }}
                QRadioButton::indicator:checked {{
                    background: {C['accent']};
                    border-color: {C['accent']};
                }}
            """)
            if i == 2:  # Default to "Recommended"
                rb.setChecked(True)

            desc_label = QLabel(desc)
            desc_label.setStyleSheet(f"""
                color: {C['text_dim']};
                font-size: 11px;
                background: transparent;
            """)

            self._btn_group.addButton(rb, i)
            self._presets.append((rb, preset_key))

            row_lay.addWidget(rb)
            row_lay.addStretch()
            row_lay.addWidget(desc_label)
            card_lay.addWidget(row)

        layout.addWidget(card)

        # ── Output format for compression ─────────────────────────────
        fmt_card = QFrame()
        fmt_card.setProperty("class", "card")
        fmt_lay = QHBoxLayout(fmt_card)
        fmt_lay.setContentsMargins(20, 14, 20, 14)
        fmt_lay.setSpacing(12)

        from PySide6.QtWidgets import QComboBox
        fmt_label = QLabel("Output format:")
        fmt_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")

        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(["MP4", "MKV", "MOV"])
        self._fmt_combo.setMinimumWidth(120)

        note = QLabel("ℹ  Compresses using H.264 — MP4 is recommended for best compatibility.")
        note.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; background: transparent;")
        note.setWordWrap(True)

        fmt_lay.addWidget(fmt_label)
        fmt_lay.addWidget(self._fmt_combo)
        fmt_lay.addStretch()

        layout.addWidget(fmt_card)
        layout.addWidget(note)
        layout.addStretch()

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def quality_preset(self) -> str:
        for rb, key in self._presets:
            if rb.isChecked():
                return key
        return "Recommended"

    @property
    def output_format(self) -> str:
        return self._fmt_combo.currentText()

    def build_ffmpeg_args(self, input_file: str, output_file: str,
                          hw_encoder: str | None = None) -> list[str]:
        codec_args = get_video_encode_args(self.output_format, self.quality_preset, hw_encoder)
        return ["-i", input_file] + codec_args + [output_file]
