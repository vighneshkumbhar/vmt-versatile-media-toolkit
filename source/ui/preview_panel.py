"""
preview_panel.py
Professional Media Preview Panel for VMT using PySide6 QtMultimedia.
Provides video/audio/image preview, interactive transport controls,
and compact ffprobe metadata display without blocking FFmpeg operations.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QStackedWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QPixmap, QImage, QColor

from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from core.ffprobe_info import probe, MediaInfo
from utils.file_utils import human_size
from utils.time_utils import seconds_to_hms
from ui.styles import COLORS as C


class MediaPreviewPanel(QFrame):
    """
    Compact Media Preview widget for the left workspace column.
    Supports video playback, audio playback, static image viewing,
    compact stream metadata display, and graceful error fallbacks.
    """

    details_requested = Signal(str)  # Emitted when user clicks "Detailed Media Info"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self._current_path: Optional[str] = None
        self._media_info: Optional[MediaInfo] = None
        self._is_sample: bool = False
        self._is_seeking: bool = False
        self._duration_ms: int = 0

        self._init_player()
        self._build_ui()

    def _init_player(self) -> None:
        """Initialize QtMultimedia player components safely."""
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)

        # Signals
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.errorOccurred.connect(self._on_player_error)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Header Row
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        self._badge_label = QLabel("MEDIA PREVIEW")
        self._badge_label.setStyleSheet(f"""
            color: {C['accent_light']};
            background-color: {C['bg_card_alt']};
            border: 1px solid {C['border']};
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            letter-spacing: 0.5px;
        """)

        self._title_label = QLabel("No file loaded")
        self._title_label.setStyleSheet(f"""
            color: {C['text_primary']};
            font-size: 12px;
            font-weight: 600;
            background: transparent;
        """)
        self._title_label.setToolTip("")

        header_row.addWidget(self._badge_label)
        header_row.addWidget(self._title_label, 1)

        # Details button link
        self._details_btn = QPushButton("Info ↗")
        self._details_btn.setFixedSize(50, 22)
        self._details_btn.setToolTip("View full ffprobe stream details")
        self._details_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {C['border']};
                color: {C['text_muted']};
                border-radius: 4px;
                font-size: 10px;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {C['bg_hover']};
                color: {C['text_primary']};
                border-color: {C['accent']};
            }}
        """)
        self._details_btn.clicked.connect(self._on_details_clicked)
        header_row.addWidget(self._details_btn)

        layout.addLayout(header_row)

        # 2. Display View Stack (Video / Audio Card / Image / Fallback)
        self._view_stack = QStackedWidget()
        self._view_stack.setMinimumHeight(180)
        self._view_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Index 0: Video Widget
        self._video_widget = QVideoWidget()
        self._video_widget.setStyleSheet(f"""
            background-color: #000000;
            border-radius: 6px;
            border: 1px solid {C['border']};
        """)
        self._player.setVideoOutput(self._video_widget)
        self._view_stack.addWidget(self._video_widget)

        # Index 1: Audio Visual Card
        self._audio_widget = QWidget()
        self._audio_widget.setStyleSheet(f"""
            background-color: {C['bg_input']};
            border-radius: 6px;
            border: 1px solid {C['border']};
        """)
        audio_lay = QVBoxLayout(self._audio_widget)
        audio_lay.setAlignment(Qt.AlignCenter)
        audio_lay.setSpacing(6)

        audio_icon = QLabel("🎵")
        audio_icon.setStyleSheet("font-size: 36px; background: transparent;")
        audio_icon.setAlignment(Qt.AlignCenter)

        self._audio_title = QLabel("Audio Stream Active")
        self._audio_title.setStyleSheet(f"color: {C['text_primary']}; font-size: 13px; font-weight: 600;")
        self._audio_title.setAlignment(Qt.AlignCenter)

        self._audio_sub = QLabel("Ready for playback")
        self._audio_sub.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px;")
        self._audio_sub.setAlignment(Qt.AlignCenter)

        audio_lay.addWidget(audio_icon)
        audio_lay.addWidget(self._audio_title)
        audio_lay.addWidget(self._audio_sub)
        self._view_stack.addWidget(self._audio_widget)

        # Index 2: Image Preview Widget
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet(f"""
            background-color: {C['bg_input']};
            border-radius: 6px;
            border: 1px solid {C['border']};
        """)
        self._view_stack.addWidget(self._image_label)

        # Index 3: Fallback / Error Widget
        self._fallback_widget = QWidget()
        self._fallback_widget.setStyleSheet(f"""
            background-color: {C['bg_input']};
            border-radius: 6px;
            border: 1px solid {C['border']};
        """)
        fb_lay = QVBoxLayout(self._fallback_widget)
        fb_lay.setAlignment(Qt.AlignCenter)
        fb_lay.setSpacing(4)

        fb_icon = QLabel("⚠️")
        fb_icon.setStyleSheet("font-size: 28px; background: transparent;")
        fb_icon.setAlignment(Qt.AlignCenter)

        self._fb_title = QLabel("Preview unavailable")
        self._fb_title.setStyleSheet(f"color: {C['text_muted']}; font-size: 12px; font-weight: 600;")
        self._fb_title.setAlignment(Qt.AlignCenter)

        self._fb_sub = QLabel("FFmpeg operations are fully available for this file.")
        self._fb_sub.setStyleSheet(f"color: {C['text_dim']}; font-size: 10px;")
        self._fb_sub.setAlignment(Qt.AlignCenter)

        fb_lay.addWidget(fb_icon)
        fb_lay.addWidget(self._fb_title)
        fb_lay.addWidget(self._fb_sub)
        self._view_stack.addWidget(self._fallback_widget)

        layout.addWidget(self._view_stack, 1)

        # 3. Transport Controls Row
        ctrl_bar = QWidget()
        ctrl_bar.setStyleSheet(f"background: transparent;")
        ctrl_lay = QVBoxLayout(ctrl_bar)
        ctrl_lay.setContentsMargins(0, 0, 0, 0)
        ctrl_lay.setSpacing(4)

        # Scrubber + Timecode Row
        scrub_row = QHBoxLayout()
        scrub_row.setSpacing(8)

        self._seek_slider = QSlider(Qt.Horizontal)
        self._seek_slider.setRange(0, 1000)
        self._seek_slider.setValue(0)
        self._seek_slider.setSingleStep(10)
        self._seek_slider.setPageStep(50)
        self._seek_slider.setFixedHeight(14)
        self._seek_slider.sliderPressed.connect(self._on_seek_start)
        self._seek_slider.sliderReleased.connect(self._on_seek_finish)

        self._time_label = QLabel("00:00 / 00:00")
        self._time_label.setFixedWidth(85)
        self._time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._time_label.setStyleSheet(f"""
            color: {C['text_muted']};
            font-family: "JetBrains Mono", "Consolas", monospace;
            font-size: 10px;
            background: transparent;
        """)

        scrub_row.addWidget(self._seek_slider, 1)
        scrub_row.addWidget(self._time_label)

        # Action Buttons Row (Play/Pause, Mute, Volume Slider)
        btns_row = QHBoxLayout()
        btns_row.setSpacing(8)

        self._play_btn = QPushButton("▶  Play")
        self._play_btn.setFixedHeight(28)
        self._play_btn.setMinimumWidth(76)
        self._play_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['accent']};
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                background-color: {C['accent_dark']};
            }}
        """)
        self._play_btn.clicked.connect(self._toggle_play_pause)

        self._mute_btn = QPushButton("🔊")
        self._mute_btn.setFixedSize(28, 28)
        self._mute_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['bg_card_alt']};
                color: {C['text_primary']};
                border: 1px solid {C['border']};
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {C['bg_hover']};
                border-color: {C['accent']};
            }}
        """)
        self._mute_btn.clicked.connect(self._toggle_mute)

        self._volume_slider = QSlider(Qt.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(80)
        self._volume_slider.setFixedWidth(70)
        self._volume_slider.setFixedHeight(14)
        self._volume_slider.setToolTip("Volume")
        self._volume_slider.valueChanged.connect(self._on_volume_changed)

        # Initial volume setting
        self._audio_output.setVolume(0.8)

        btns_row.addWidget(self._play_btn)
        btns_row.addWidget(self._mute_btn)
        btns_row.addWidget(self._volume_slider)
        btns_row.addStretch()

        ctrl_lay.addLayout(scrub_row)
        ctrl_lay.addLayout(btns_row)

        layout.addWidget(ctrl_bar)

        # 4. Compact Stream Metadata Pills
        self._meta_card = QFrame()
        self._meta_card.setStyleSheet(f"""
            QFrame {{
                background-color: {C['bg_input']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                padding: 4px 8px;
            }}
        """)
        meta_lay = QHBoxLayout(self._meta_card)
        meta_lay.setContentsMargins(4, 4, 4, 4)
        meta_lay.setSpacing(6)

        self._meta_label = QLabel("No metadata available")
        self._meta_label.setStyleSheet(f"""
            color: {C['text_muted']};
            font-size: 11px;
            background: transparent;
        """)
        self._meta_label.setWordWrap(True)

        meta_lay.addWidget(self._meta_label)
        layout.addWidget(self._meta_card)

    # ── Public API ─────────────────────────────────────────────────────────────

    def load_media(self, file_path: str, is_sample: bool = False) -> None:
        """
        Loads a file into the preview player and displays metadata.
        DOES NOT AUTOPLAY VIDEO OR AUDIO. Keeps player PAUSED at 00:00.
        """
        self._stop_playback()
        self._current_path = file_path
        self._is_sample = is_sample

        if not file_path or not os.path.exists(file_path):
            self._show_fallback("File not found", "Selected file path does not exist.")
            return

        basename = Path(file_path).name
        if is_sample:
            self._badge_label.setText("SAMPLE MEDIA")
            self._badge_label.setStyleSheet(f"""
                color: {C['accent_light']};
                background-color: {C['bg_card_alt']};
                border: 1px solid {C['accent']};
                border-radius: 4px;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 6px;
            """)
            self._title_label.setText(f"VMT Preview · {basename}")
        else:
            self._badge_label.setText("PREVIEW")
            self._badge_label.setStyleSheet(f"""
                color: {C['success']};
                background-color: {C['bg_card_alt']};
                border: 1px solid {C['border']};
                border-radius: 4px;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 6px;
            """)
            self._title_label.setText(basename)

        self._title_label.setToolTip(file_path)

        # Extract stream info via ffprobe
        from core.ffmpeg_finder import find_ffprobe
        ffprobe_bin = getattr(self, "_ffprobe_path", "") or find_ffprobe() or ""
        try:
            if ffprobe_bin and os.path.exists(ffprobe_bin):
                self._media_info = probe(ffprobe_bin, file_path)
                self._update_metadata_display()
            else:
                self._media_info = None
                self._meta_label.setText("ffprobe path not set")
        except Exception:
            self._media_info = None
            self._meta_label.setText("Metadata extraction pending...")

        # Determine media preview mode (Video, Audio, Image, Unsupported)
        ext = Path(file_path).suffix.lower()

        if ext in ('.png', '.jpg', '.jpeg', '.bmp', '.webp'):
            # Image Preview Mode
            pix = QPixmap(file_path)
            if not pix.isNull():
                scaled = pix.scaled(320, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._image_label.setPixmap(scaled)
                self._view_stack.setCurrentIndex(2)
                self._set_controls_enabled(False)
            else:
                self._show_fallback("Image format error", "Could not render static image.")
            return

        # Audio / Video QtMultimedia handling
        self._set_controls_enabled(True)
        url = QUrl.fromLocalFile(os.path.abspath(file_path))
        self._player.setSource(url)

        # Ensure paused state at startup / load
        self._player.pause()
        self._play_btn.setText("▶  Play")

        if self._media_info and self._media_info.has_video:
            self._view_stack.setCurrentIndex(0)
        elif self._media_info and self._media_info.has_audio:
            self._audio_title.setText(basename)
            self._audio_sub.setText(f"Audio Track · {self._media_info.audio_codec.upper()}")
            self._view_stack.setCurrentIndex(1)
        elif ext in ('.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv', '.wmv', '.m4v', '.ts'):
            self._view_stack.setCurrentIndex(0)
        elif ext in ('.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.opus', '.wma'):
            self._audio_title.setText(basename)
            self._audio_sub.setText("Audio Stream Ready")
            self._view_stack.setCurrentIndex(1)
        else:
            self._show_fallback("Preview unavailable", "Format not supported by Qt Multimedia preview player.")

    def clear(self) -> None:
        """Resets the preview panel state."""
        self._stop_playback()
        self._current_path = None
        self._media_info = None
        self._badge_label.setText("MEDIA PREVIEW")
        self._title_label.setText("No file loaded")
        self._title_label.setToolTip("")
        self._meta_label.setText("No metadata available")
        self._show_fallback("No file loaded", "Drag and drop media files to begin.")

    # ── Playback & Control Handlers ────────────────────────────────────────────

    def _toggle_play_pause(self) -> None:
        if not self._current_path:
            return
        state = self._player.playbackState()
        if state == QMediaPlayer.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _toggle_mute(self) -> None:
        is_muted = self._audio_output.isMuted()
        self._audio_output.setMuted(not is_muted)
        self._mute_btn.setText("🔇" if not is_muted else "🔊")

    def _on_volume_changed(self, value: int) -> None:
        vol = float(value) / 100.0
        self._audio_output.setVolume(vol)

    def _on_seek_start(self) -> None:
        self._is_seeking = True

    def _on_seek_finish(self) -> None:
        if self._duration_ms > 0:
            val = self._seek_slider.value()
            target_ms = int((val / 1000.0) * self._duration_ms)
            self._player.setPosition(target_ms)
        self._is_seeking = False

    def _on_position_changed(self, position_ms: int) -> None:
        if self._is_seeking or self._duration_ms <= 0:
            return
        pct = int((position_ms / float(self._duration_ms)) * 1000.0)
        self._seek_slider.setValue(pct)

        cur_sec = position_ms // 1000
        dur_sec = self._duration_ms // 1000
        self._time_label.setText(f"{seconds_to_hms(cur_sec)} / {seconds_to_hms(dur_sec)}")

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._duration_ms = duration_ms
        cur_sec = self._player.position() // 1000
        dur_sec = duration_ms // 1000
        self._time_label.setText(f"{seconds_to_hms(cur_sec)} / {seconds_to_hms(dur_sec)}")

    def _on_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlayingState:
            self._play_btn.setText("⏸  Pause")
            self._play_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {C['accent_dark']};
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 0 10px;
                }}
            """)
        else:
            self._play_btn.setText("▶  Play")
            self._play_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {C['accent']};
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 0 10px;
                }}
                QPushButton:hover {{
                    background-color: {C['accent_dark']};
                }}
            """)

    def _on_player_error(self, error, error_string: str) -> None:
        """Gracefully handle QtMultimedia error without crashing VMT."""
        self._show_fallback("Preview unavailable", f"Playback issue: {error_string or 'Codec unsupported'}")

    def _on_details_clicked(self) -> None:
        if self._current_path:
            self.details_requested.emit(self._current_path)

    def _stop_playback(self) -> None:
        try:
            self._player.stop()
        except Exception:
            pass

    def _show_fallback(self, title: str, subtitle: str) -> None:
        self._fb_title.setText(title)
        self._fb_sub.setText(subtitle)
        self._view_stack.setCurrentIndex(3)
        self._set_controls_enabled(False)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._play_btn.setEnabled(enabled)
        self._seek_slider.setEnabled(enabled)
        self._mute_btn.setEnabled(enabled)
        self._volume_slider.setEnabled(enabled)

    def _update_metadata_display(self) -> None:
        if not self._media_info:
            self._meta_label.setText("No metadata available")
            return

        info = self._media_info
        v = info.primary_video
        a = info.primary_audio
        parts = []

        if v:
            res = f"{v.width}×{v.height}" if v.width and v.height else ""
            if res:
                parts.append(res)
            if v.codec_name:
                parts.append(v.codec_name.upper())
            if v.fps > 0:
                parts.append(f"{v.fps:.1f} FPS")

        if a:
            if a.codec_name:
                parts.append(f"Audio: {a.codec_name.upper()}")

        if info.duration > 0:
            parts.append(seconds_to_hms(int(info.duration)))

        if info.file_size > 0:
            parts.append(human_size(info.file_size))

        if parts:
            self._meta_label.setText(" · ".join(parts))
        else:
            self._meta_label.setText("Stream format detected")
