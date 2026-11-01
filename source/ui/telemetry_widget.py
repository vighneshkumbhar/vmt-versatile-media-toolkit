"""
telemetry_widget.py
Cyberpunk-style Hardware Acceleration and Encoding Bandwidth Telemetry Card.
Features a live animated audio/processing waveform visualizer in Cyber Mint.
"""
from __future__ import annotations
import math
import random
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient, QFont

from ui.styles import COLORS as C


class WaveformVisualizerWidget(QWidget):
    """
    Renders dynamic equalizer/waveform audio & encoding bars in glowing Cyber Mint.
    """

    def __init__(self, bar_count: int = 36, parent=None):
        super().__init__(parent)
        self.bar_count = bar_count
        self.setFixedHeight(36)
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Baseline bar heights (normalized 0.1 to 1.0)
        self._bars = [0.2 + 0.6 * math.sin(i * 0.3) ** 2 for i in range(bar_count)]
        self._is_active = False

        # Animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_step)
        self._timer.start(80) # 12.5 fps smooth subtle animation

    def set_active(self, active: bool):
        self._is_active = active
        self.update()

    def _animate_step(self):
        if self._is_active:
            # Active processing wave animation
            self._bars = [
                max(0.15, min(1.0, b + random.uniform(-0.18, 0.18)))
                for b in self._bars
            ]
        else:
            # Subtle resting idle wave
            t = (self._bars[0] * 10) % (2 * math.pi)
            self._bars = [
                0.2 + 0.35 * abs(math.sin(i * 0.25 + t))
                for i in range(self.bar_count)
            ]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        bar_width = max(2.0, (width - (self.bar_count - 1) * 3) / self.bar_count)
        spacing = 3.0

        for i, val in enumerate(self._bars):
            bar_h = max(4.0, val * (height - 6))
            x = i * (bar_width + spacing)
            y = (height - bar_h) / 2.0

            # Gradient from mint to bright neon
            gradient = QLinearGradient(x, y, x, y + bar_h)
            if self._is_active:
                gradient.setColorAt(0.0, QColor("#67F5BA"))
                gradient.setColorAt(1.0, QColor("#1E9E68"))
            else:
                gradient.setColorAt(0.0, QColor("#2FE69A"))
                gradient.setColorAt(1.0, QColor("#14533A"))

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(QRectF(x, y, bar_width, bar_h), 1.5, 1.5)


class TelemetryHeroCard(QFrame):
    """
    Top telemetry panel displaying:
      - Processing Bandwidth (e.g. 8.4 GB/min or active encoding fps/bitrate)
      - Cyber Mint waveform equalizer
      - Hardware Encoder status badge (e.g. NVIDIA NVENC / Intel QSV / AMD AMF)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "hero-telemetry")
        self.setFixedHeight(74)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(24)

        # ── Left: Processing Bandwidth Metric ──────────────────────
        left_col = QVBoxLayout()
        left_col.setSpacing(2)

        sub_label = QLabel("PROCESSING BANDWIDTH")
        sub_label.setStyleSheet(f"""
            color: {C['text_dim']};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.2px;
            background: transparent;
        """)
        left_col.addWidget(sub_label)

        metric_row = QHBoxLayout()
        metric_row.setSpacing(6)
        self._metric_val = QLabel("8.4")
        self._metric_val.setStyleSheet(f"""
            color: #FFFFFF;
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: transparent;
        """)
        self._metric_unit = QLabel("GB/min")
        self._metric_unit.setStyleSheet(f"""
            color: {C['text_muted']};
            font-size: 11px;
            font-weight: 600;
            margin-top: 8px;
            background: transparent;
        """)
        metric_row.addWidget(self._metric_val)
        metric_row.addWidget(self._metric_unit)
        metric_row.addStretch()
        left_col.addLayout(metric_row)

        layout.addLayout(left_col)

        # ── Center: Equalizer Waveform ─────────────────────────────
        self._waveform = WaveformVisualizerWidget(bar_count=38)
        layout.addWidget(self._waveform, 1)

        # ── Right: Hardware Encoder Badge ──────────────────────────
        badge_frame = QFrame()
        badge_frame.setProperty("class", "telemetry-badge")
        badge_lay = QHBoxLayout(badge_frame)
        badge_lay.setContentsMargins(12, 6, 14, 6)
        badge_lay.setSpacing(8)

        chip_icon = QLabel("⬡")
        chip_icon.setStyleSheet(f"color: {C['accent']}; font-size: 14px; font-weight: 900; background: transparent;")

        self._hw_label = QLabel("NVIDIA NVENC")
        self._hw_label.setStyleSheet(f"""
            color: {C['accent']};
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.8px;
            background: transparent;
        """)

        badge_lay.addWidget(chip_icon)
        badge_lay.addWidget(self._hw_label)
        layout.addWidget(badge_frame)

    def set_active_processing(self, active: bool, speed_str: str = "8.4", unit_str: str = "GB/min"):
        self._waveform.set_active(active)
        self._metric_val.setText(speed_str)
        self._metric_unit.setText(unit_str)

    def set_hw_encoder_name(self, name: str):
        self._hw_label.setText(name.upper())
