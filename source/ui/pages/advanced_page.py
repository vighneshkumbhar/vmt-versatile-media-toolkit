"""
advanced_page.py
Advanced / custom FFmpeg settings panel (hidden by default).
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QFrame, QCheckBox, QSpinBox, QPlainTextEdit
)
from PySide6.QtCore import Signal

from ui.styles import COLORS as C


class AdvancedPage(QWidget):
    """Expose deeper FFmpeg controls for experienced users."""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hw_encoders: dict[str, bool] = {"nvenc": False, "qsv": False, "amf": False}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── Warning banner ────────────────────────────────────────────
        warn = QFrame()
        warn.setStyleSheet(f"""
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 8px;
        """)
        warn_lay = QHBoxLayout(warn)
        warn_lay.setContentsMargins(14, 10, 14, 10)
        warn_icon = QLabel("⚙")
        warn_icon.setStyleSheet(f"color: {C['accent']}; font-size: 18px; background: transparent;")
        warn_text = QLabel(
            "Advanced mode. These settings override the operation page settings for the current job."
        )
        warn_text.setStyleSheet(f"color: {C['accent_light']}; font-size: 12px; background: transparent;")
        warn_text.setWordWrap(True)
        warn_lay.addWidget(warn_icon)
        warn_lay.addWidget(warn_text)

        # ── Codec card ────────────────────────────────────────────────
        codec_card = self._card()
        cc_lay = QVBoxLayout(codec_card)
        cc_lay.setContentsMargins(20, 16, 20, 16)
        cc_lay.setSpacing(12)
        cc_lay.addWidget(self._section("CODEC SETTINGS"))

        # Video codec
        vc_row = QHBoxLayout()
        vc_label = QLabel("Video codec:")
        vc_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        vc_label.setFixedWidth(110)
        self._vcodec_combo = QComboBox()
        self._vcodec_combo.addItems([
            "Auto", "libx264", "libx265", "libvpx-vp9", "mpeg4",
            "h264_nvenc", "h264_qsv", "h264_amf",
            "hevc_nvenc", "hevc_qsv",
        ])
        self._vcodec_combo.setMinimumWidth(160)
        vc_row.addWidget(vc_label)
        vc_row.addWidget(self._vcodec_combo)
        vc_row.addStretch()

        # Audio codec
        ac_row = QHBoxLayout()
        ac_label = QLabel("Audio codec:")
        ac_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        ac_label.setFixedWidth(110)
        self._acodec_combo = QComboBox()
        self._acodec_combo.addItems([
            "Auto", "aac", "libmp3lame", "libopus", "libvorbis",
            "flac", "pcm_s16le", "copy",
        ])
        self._acodec_combo.setMinimumWidth(160)
        ac_row.addWidget(ac_label)
        ac_row.addWidget(self._acodec_combo)
        ac_row.addStretch()

        # CRF
        crf_row = QHBoxLayout()
        crf_label = QLabel("CRF / Quality:")
        crf_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        crf_label.setFixedWidth(110)
        self._crf_spin = QSpinBox()
        self._crf_spin.setRange(0, 63)
        self._crf_spin.setValue(23)
        self._crf_spin.setFixedWidth(80)
        crf_note = QLabel("0 = lossless · 23 = default · 51 = worst")
        crf_note.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; background: transparent;")
        crf_row.addWidget(crf_label)
        crf_row.addWidget(self._crf_spin)
        crf_row.addSpacing(10)
        crf_row.addWidget(crf_note)
        crf_row.addStretch()

        # Preset
        preset_row = QHBoxLayout()
        preset_label = QLabel("Preset:")
        preset_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        preset_label.setFixedWidth(110)
        self._preset_combo = QComboBox()
        self._preset_combo.addItems([
            "ultrafast", "superfast", "veryfast", "faster", "fast",
            "medium", "slow", "slower", "veryslow"
        ])
        self._preset_combo.setCurrentText("medium")
        self._preset_combo.setMinimumWidth(130)
        preset_row.addWidget(preset_label)
        preset_row.addWidget(self._preset_combo)
        preset_row.addStretch()

        # Bitrate override
        br_row = QHBoxLayout()
        br_label = QLabel("Video bitrate:")
        br_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        br_label.setFixedWidth(110)
        self._vbr_edit = QLineEdit()
        self._vbr_edit.setPlaceholderText("e.g. 2M  (leave blank for CRF mode)")
        self._vbr_edit.setMinimumWidth(180)
        br_note = QLabel("Overrides CRF if set")
        br_note.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; background: transparent;")
        br_row.addWidget(br_label)
        br_row.addWidget(self._vbr_edit)
        br_row.addSpacing(10)
        br_row.addWidget(br_note)
        br_row.addStretch()

        # FPS
        fps_row = QHBoxLayout()
        fps_label = QLabel("Frame rate:")
        fps_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        fps_label.setFixedWidth(110)
        self._fps_edit = QLineEdit()
        self._fps_edit.setPlaceholderText("e.g. 30  (leave blank to keep original)")
        self._fps_edit.setMinimumWidth(180)
        fps_row.addWidget(fps_label)
        fps_row.addWidget(self._fps_edit)
        fps_row.addStretch()

        cc_lay.addLayout(vc_row)
        cc_lay.addLayout(ac_row)
        cc_lay.addLayout(crf_row)
        cc_lay.addLayout(preset_row)
        cc_lay.addLayout(br_row)
        cc_lay.addLayout(fps_row)

        # ── Hardware acceleration card ─────────────────────────────────
        hw_card = self._card()
        hw_lay = QVBoxLayout(hw_card)
        hw_lay.setContentsMargins(20, 16, 20, 16)
        hw_lay.setSpacing(10)
        hw_lay.addWidget(self._section("HARDWARE ACCELERATION"))

        self._hw_note = QLabel("Detecting hardware encoders…")
        self._hw_note.setStyleSheet(f"color: {C['text_dim']}; font-size: 12px; background: transparent;")
        self._hw_note.setWordWrap(True)
        hw_lay.addWidget(self._hw_note)

        hw_desc = QLabel(
            "Hardware encoding is usually faster, but CPU encoding produces better quality\n"
            "at the same file size. Use hardware for speed, CPU for quality."
        )
        hw_desc.setStyleSheet(f"color: {C['text_muted']}; font-size: 12px; background: transparent;")
        hw_lay.addWidget(hw_desc)

        # ── Custom args card ──────────────────────────────────────────
        custom_card = self._card()
        custom_lay = QVBoxLayout(custom_card)
        custom_lay.setContentsMargins(20, 16, 20, 16)
        custom_lay.setSpacing(10)
        custom_lay.addWidget(self._section("CUSTOM FFmpeg ARGUMENTS"))

        custom_note = QLabel("Additional arguments appended after the codec args (before output).")
        custom_note.setStyleSheet(f"color: {C['text_dim']}; font-size: 12px; background: transparent;")

        self._custom_args_edit = QLineEdit()
        self._custom_args_edit.setPlaceholderText("e.g.  -map 0:v -map 0:a:0  -metadata title=MyVideo")
        self._custom_args_edit.setMinimumWidth(300)

        custom_lay.addWidget(custom_note)
        custom_lay.addWidget(self._custom_args_edit)

        layout.addWidget(warn)
        layout.addWidget(codec_card)
        layout.addWidget(hw_card)
        layout.addWidget(custom_card)
        layout.addStretch()

    def _card(self) -> QFrame:
        f = QFrame()
        f.setProperty("class", "card")
        return f

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['text_dim']}; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent;")
        return lbl

    # ── Public API ─────────────────────────────────────────────────────────

    def update_hw_encoders(self, encoders: dict[str, bool]) -> None:
        self._hw_encoders = encoders
        available = [k.upper() for k, v in encoders.items() if v]
        if available:
            self._hw_note.setText(f"✓  Available: {', '.join(available)}")
            self._hw_note.setStyleSheet(f"color: {C['success']}; font-size: 12px; background: transparent;")
        else:
            self._hw_note.setText("No hardware encoders detected. CPU encoding will be used.")
            self._hw_note.setStyleSheet(f"color: {C['text_dim']}; font-size: 12px; background: transparent;")

    def get_extra_args(self) -> list[str]:
        """
        Build list of extra args from advanced settings.
        Returns empty list if all settings are default/auto.
        """
        args = []
        vc = self._vcodec_combo.currentText()
        if vc != "Auto":
            args += ["-c:v", vc]

        ac = self._acodec_combo.currentText()
        if ac != "Auto":
            args += ["-c:a", ac]

        if vc != "Auto" and vc not in ("copy",):
            crf = self._crf_spin.value()
            vbr = self._vbr_edit.text().strip()
            if vbr:
                args += ["-b:v", vbr]
            else:
                args += ["-crf", str(crf)]

            if vc in ("libx264", "libx265"):
                preset = self._preset_combo.currentText()
                args += ["-preset", preset]

        fps = self._fps_edit.text().strip()
        if fps:
            args += ["-r", fps]

        custom = self._custom_args_edit.text().strip()
        if custom:
            import shlex
            try:
                args += shlex.split(custom)
            except ValueError:
                args += custom.split()

        return args

    @property
    def is_default(self) -> bool:
        """True if all settings are at defaults (no override needed)."""
        return (
            self._vcodec_combo.currentText() == "Auto" and
            self._acodec_combo.currentText() == "Auto" and
            not self._vbr_edit.text().strip() and
            not self._fps_edit.text().strip() and
            not self._custom_args_edit.text().strip()
        )
