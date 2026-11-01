"""
resize_page.py
The "Resize / Scale" operation panel.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QSpinBox, QFrame
)
from PySide6.QtCore import Qt, Signal

from core.presets import (
    RESOLUTION_PRESETS, QUALITY_PRESETS,
    get_video_encode_args, get_resize_filter
)
from ui.styles import COLORS as C


class ResizePage(QWidget):
    """Scale video to a different resolution."""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── Resolution card ───────────────────────────────────────────
        res_card = QFrame()
        res_card.setProperty("class", "card")
        res_lay = QVBoxLayout(res_card)
        res_lay.setContentsMargins(20, 16, 20, 16)
        res_lay.setSpacing(12)

        title = QLabel("RESOLUTION")
        title.setStyleSheet(f"color: {C['text_dim']}; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent;")
        res_lay.addWidget(title)

        preset_row = QHBoxLayout()
        preset_label = QLabel("Target size:")
        preset_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        preset_label.setFixedWidth(90)

        self._preset_combo = QComboBox()
        self._preset_combo.addItems(list(RESOLUTION_PRESETS.keys()))
        self._preset_combo.setCurrentText("720p")
        self._preset_combo.setMinimumWidth(160)
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)

        preset_row.addWidget(preset_label)
        preset_row.addWidget(self._preset_combo)
        preset_row.addStretch()
        res_lay.addLayout(preset_row)

        # Custom size row
        self._custom_row = QHBoxLayout()
        w_label = QLabel("Width:")
        w_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        w_label.setFixedWidth(90)

        self._width_spin = QSpinBox()
        self._width_spin.setRange(64, 7680)
        self._width_spin.setValue(1280)
        self._width_spin.setSingleStep(2)
        self._width_spin.setFixedWidth(100)

        h_label = QLabel("Height:")
        h_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")

        self._height_spin = QSpinBox()
        self._height_spin.setRange(64, 4320)
        self._height_spin.setValue(720)
        self._height_spin.setSingleStep(2)
        self._height_spin.setFixedWidth(100)

        self._custom_row.addWidget(w_label)
        self._custom_row.addWidget(self._width_spin)
        self._custom_row.addSpacing(16)
        self._custom_row.addWidget(h_label)
        self._custom_row.addWidget(self._height_spin)
        self._custom_row.addStretch()

        # Aspect ratio checkbox
        self._aspect_check = QCheckBox("Keep aspect ratio (recommended)")
        self._aspect_check.setChecked(True)
        self._aspect_check.setStyleSheet(f"""
            QCheckBox {{ color: {C['text_primary']}; background: transparent; spacing: 8px; }}
            QCheckBox::indicator {{
                width: 18px; height: 18px;
                border-radius: 5px;
                border: 2px solid {C['border']};
                background: {C['bg_input']};
            }}
            QCheckBox::indicator:checked {{
                background: {C['accent']};
                border-color: {C['accent']};
            }}
        """)

        res_lay.addLayout(self._custom_row)
        res_lay.addWidget(self._aspect_check)

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

        fmt_label = QLabel("Format:")
        fmt_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")

        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(["MP4", "MKV", "MOV"])
        self._fmt_combo.setMinimumWidth(100)

        q_lay.addWidget(q_label)
        q_lay.addWidget(self._quality_combo)
        q_lay.addSpacing(20)
        q_lay.addWidget(fmt_label)
        q_lay.addWidget(self._fmt_combo)
        q_lay.addStretch()

        note = QLabel("ℹ  Videos are always re-encoded when resizing.")
        note.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; background: transparent;")

        layout.addWidget(res_card)
        layout.addWidget(q_card)
        layout.addWidget(note)
        layout.addStretch()

        # Init
        self._on_preset_changed("720p")

    def _on_preset_changed(self, preset: str) -> None:
        is_custom = (preset == "Custom")
        # Show/hide custom width/height
        for i in range(self._custom_row.count()):
            item = self._custom_row.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(is_custom)

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def resolution(self) -> tuple[int, int] | None:
        preset = self._preset_combo.currentText()
        if preset == "Custom":
            return self._width_spin.value(), self._height_spin.value()
        return RESOLUTION_PRESETS.get(preset)

    @property
    def keep_aspect(self) -> bool:
        return self._aspect_check.isChecked()

    @property
    def quality(self) -> str:
        return self._quality_combo.currentText()

    @property
    def output_format(self) -> str:
        return self._fmt_combo.currentText()

    def build_ffmpeg_args(self, input_file: str, output_file: str,
                          hw_encoder: str | None = None) -> list[str]:
        res = self.resolution
        if res:
            w, h = res
            filter_args = get_resize_filter(w, h, self.keep_aspect)
        else:
            filter_args = []  # Original — just re-encode

        codec_args = get_video_encode_args(self.output_format, self.quality, hw_encoder)

        # Merge filter into codec args (replace -vf if already present)
        if filter_args and "-vf" in codec_args:
            idx = codec_args.index("-vf")
            existing = codec_args[idx + 1]
            # Prepend resize filter
            codec_args[idx + 1] = filter_args[1] + "," + existing
            extra = []
        else:
            extra = filter_args

        return ["-i", input_file] + extra + codec_args + [output_file]
