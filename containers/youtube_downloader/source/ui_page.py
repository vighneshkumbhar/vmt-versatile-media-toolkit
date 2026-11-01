"""
ui_page.py
PySide6 User Interface Page for VMT YouTube Downloader Extension.
"""
import os
import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFrame, QProgressBar, QFileDialog,
    QMessageBox, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QFont, QPixmap, QImage, QDesktopServices
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

try:
    from .downloader import FetchMetadataThread, DownloadVideoThread, is_ytdlp_available
except ImportError:
    from downloader import FetchMetadataThread, DownloadVideoThread, is_ytdlp_available

logger = logging.getLogger(__name__)

# Dark theme visual colors consistent with VMT
COLORS = {
    'bg_base': '#121417',
    'bg_dark': '#1a1d24',
    'bg_card': '#222631',
    'bg_card_alt': '#2a2f3d',
    'bg_hover': '#32384a',
    'border': '#2d3345',
    'text_primary': '#ffffff',
    'text_muted': '#9ca3af',
    'text_dim': '#6b7280',
    'accent': '#ef4444',       # YouTube Red
    'accent_dark': '#dc2626',
    'accent_light': '#f87171',
    'success': '#2ecc71',
    'warning': '#f1c40f',
}


class YouTubeDownloaderPage(QWidget):
    """
    Main user interface page for the YouTube Downloader extension.
    """

    def __init__(self, ffmpeg_path: str = "", parent=None):
        super().__init__(parent)
        self.ffmpeg_path = ffmpeg_path
        self.meta_thread: Optional[FetchMetadataThread] = None
        self.download_thread: Optional[DownloadVideoThread] = None
        self.last_output_path = ""
        self.net_manager = QNetworkAccessManager(self)
        self.net_manager.finished.connect(self._on_thumbnail_downloaded)

        self._build_ui()

    def set_ffmpeg_path(self, path: str):
        self.ffmpeg_path = path

    def _build_ui(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(20, 20, 20, 20)
        root_lay.setSpacing(16)

        # Header Title
        header_lay = QHBoxLayout()
        icon_lbl = QLabel("▶")
        icon_lbl.setStyleSheet(f"font-size: 26px; color: {COLORS['accent']}; background: transparent;")
        header_lay.addWidget(icon_lbl)

        title_lbl = QLabel("YouTube Downloader")
        title_lbl.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {COLORS['text_primary']}; background: transparent;")
        header_lay.addWidget(title_lbl)
        header_lay.addStretch()

        root_lay.addLayout(header_lay)

        # Main scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        c_lay = QVBoxLayout(content_widget)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(16)

        # ── 1. URL Input Section Card ──────────────────────────────────────────────
        url_card = QFrame()
        url_card.setStyleSheet(f"background: {COLORS['bg_card']}; border-radius: 12px; border: 1px solid {COLORS['border']};")
        uc_lay = QVBoxLayout(url_card)
        uc_lay.setContentsMargins(20, 18, 20, 18)
        uc_lay.setSpacing(12)

        lbl_url = QLabel("YOUTUBE URL")
        lbl_url.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; font-weight: 800; letter-spacing: 1px; background: transparent;")
        uc_lay.addWidget(lbl_url)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']}; border-radius: 8px;
                padding: 10px 14px; color: white; font-size: 14px;
            }}
            QLineEdit:focus {{ border: 1px solid {COLORS['accent']}; }}
        """)
        input_row.addWidget(self.url_edit, 1)

        self.btn_fetch = QPushButton("Get Information")
        self.btn_fetch.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']}; color: white; border: none; border-radius: 8px;
                padding: 10px 22px; font-size: 14px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {COLORS['accent_dark']}; }}
        """)
        self.btn_fetch.clicked.connect(self._on_fetch_clicked)
        input_row.addWidget(self.btn_fetch)

        uc_lay.addLayout(input_row)
        c_lay.addWidget(url_card)

        # ── 2. Video Metadata Preview Card ─────────────────────────────────────────
        self.meta_card = QFrame()
        self.meta_card.setStyleSheet(f"background: {COLORS['bg_card']}; border-radius: 12px; border: 1px solid {COLORS['border']};")
        mc_lay = QHBoxLayout(self.meta_card)
        mc_lay.setContentsMargins(18, 18, 18, 18)
        mc_lay.setSpacing(18)

        self.thumb_lbl = QLabel("No Image")
        self.thumb_lbl.setFixedSize(160, 90)
        self.thumb_lbl.setAlignment(Qt.AlignCenter)
        self.thumb_lbl.setStyleSheet(f"background: {COLORS['bg_dark']}; border-radius: 8px; color: {COLORS['text_dim']}; font-size: 12px; border: 1px solid {COLORS['border']};")
        mc_lay.addWidget(self.thumb_lbl)

        meta_info_lay = QVBoxLayout()
        meta_info_lay.setSpacing(6)

        self.title_lbl = QLabel("Paste a YouTube URL and click 'Get Information'")
        self.title_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 15px; font-weight: 700; background: transparent;")
        self.title_lbl.setWordWrap(True)
        meta_info_lay.addWidget(self.title_lbl)

        self.dur_lbl = QLabel("Duration: --:--")
        self.dur_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px; background: transparent;")
        meta_info_lay.addWidget(self.dur_lbl)
        meta_info_lay.addStretch()

        mc_lay.addLayout(meta_info_lay, 1)
        c_lay.addWidget(self.meta_card)

        # ── 3. Options & Download Card ─────────────────────────────────────────────
        opt_card = QFrame()
        opt_card.setStyleSheet(f"background: {COLORS['bg_card']}; border-radius: 12px; border: 1px solid {COLORS['border']};")
        oc_lay = QVBoxLayout(opt_card)
        oc_lay.setContentsMargins(20, 18, 20, 18)
        oc_lay.setSpacing(14)

        lbl_opt = QLabel("DOWNLOAD OPTIONS")
        lbl_opt.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; font-weight: 800; letter-spacing: 1px; background: transparent;")
        oc_lay.addWidget(lbl_opt)

        opts_row = QHBoxLayout()
        opts_row.setSpacing(14)

        # Mode
        m_lay = QVBoxLayout()
        m_lay.setSpacing(4)
        lbl_m = QLabel("Type:")
        lbl_m.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; background: transparent;")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Video & Audio", "Audio Only"])
        self.mode_combo.setStyleSheet(f"background: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 6px 10px; color: white;")
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        m_lay.addWidget(lbl_m)
        m_lay.addWidget(self.mode_combo)
        opts_row.addLayout(m_lay)

        # Quality
        q_lay = QVBoxLayout()
        q_lay.setSpacing(4)
        lbl_q = QLabel("Quality:")
        lbl_q.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; background: transparent;")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Best available", "1080p", "720p", "480p", "360p"])
        self.quality_combo.setStyleSheet(f"background: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 6px 10px; color: white;")
        q_lay.addWidget(lbl_q)
        q_lay.addWidget(self.quality_combo)
        opts_row.addLayout(q_lay)

        # Format
        f_lay = QVBoxLayout()
        f_lay.setSpacing(4)
        lbl_f = QLabel("Format:")
        lbl_f.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; background: transparent;")
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["MP4", "MKV"])
        self.fmt_combo.setStyleSheet(f"background: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 6px 10px; color: white;")
        f_lay.addWidget(lbl_f)
        f_lay.addWidget(self.fmt_combo)
        opts_row.addLayout(f_lay)

        oc_lay.addLayout(opts_row)

        # Output Folder Row
        folder_row = QHBoxLayout()
        folder_row.setSpacing(10)

        self.out_edit = QLineEdit()
        default_out = str(Path.home() / "Downloads")
        self.out_edit.setText(default_out)
        self.out_edit.setStyleSheet(f"background: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 8px 12px; color: white;")
        folder_row.addWidget(self.out_edit, 1)

        btn_browse = QPushButton("Browse")
        btn_browse.setStyleSheet(f"background: {COLORS['bg_card_alt']}; color: white; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 8px 16px;")
        btn_browse.clicked.connect(self._on_browse_clicked)
        folder_row.addWidget(btn_browse)

        self.btn_download = QPushButton("Download")
        self.btn_download.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']}; color: white; border: none; border-radius: 6px;
                padding: 8px 24px; font-weight: bold; font-size: 14px;
            }}
            QPushButton:hover {{ background: {COLORS['accent_dark']}; }}
        """)
        self.btn_download.clicked.connect(self._on_download_clicked)
        folder_row.addWidget(self.btn_download)

        oc_lay.addLayout(folder_row)
        c_lay.addWidget(opt_card)

        # ── 4. Progress & Status Card ──────────────────────────────────────────────
        self.prog_card = QFrame()
        self.prog_card.setStyleSheet(f"background: {COLORS['bg_card']}; border-radius: 12px; border: 1px solid {COLORS['border']};")
        pc_lay = QVBoxLayout(self.prog_card)
        pc_lay.setContentsMargins(20, 18, 20, 18)
        pc_lay.setSpacing(12)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px; font-weight: 600; background: transparent;")
        pc_lay.addWidget(self.status_lbl)

        self.prog_bar = QProgressBar()
        self.prog_bar.setFixedHeight(10)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setStyleSheet(f"""
            QProgressBar {{ background: {COLORS['bg_dark']}; border-radius: 5px; border: none; }}
            QProgressBar::chunk {{ background: {COLORS['accent']}; border-radius: 5px; }}
        """)
        pc_lay.addWidget(self.prog_bar)

        act_row = QHBoxLayout()
        self.speed_lbl = QLabel("")
        self.speed_lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px; background: transparent;")
        act_row.addWidget(self.speed_lbl)
        act_row.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet(f"background: {COLORS['bg_dark']}; color: {COLORS['text_muted']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 6px 14px; font-size: 12px;")
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        self.btn_cancel.hide()
        act_row.addWidget(self.btn_cancel)

        self.btn_open_loc = QPushButton("Open Output Location")
        self.btn_open_loc.setStyleSheet(f"background: {COLORS['success']}; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-weight: bold; font-size: 12px;")
        self.btn_open_loc.clicked.connect(self._on_open_location_clicked)
        self.btn_open_loc.hide()
        act_row.addWidget(self.btn_open_loc)

        pc_lay.addLayout(act_row)
        c_lay.addWidget(self.prog_card)

        c_lay.addStretch()
        scroll.setWidget(content_widget)
        root_lay.addWidget(scroll)

    def _on_mode_changed(self, mode_text: str):
        self.fmt_combo.clear()
        if mode_text == "Audio Only":
            self.fmt_combo.addItems(["MP3", "M4A", "WAV"])
            self.quality_combo.setEnabled(False)
        else:
            self.fmt_combo.addItems(["MP4", "MKV"])
            self.quality_combo.setEnabled(True)

    def _on_browse_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.out_edit.text())
        if folder:
            self.out_edit.setText(folder)

    def _on_fetch_clicked(self):
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Empty URL", "Please enter a valid YouTube URL.")
            return

        self.btn_fetch.setEnabled(False)
        self.btn_fetch.setText("Fetching...")
        self.title_lbl.setText("Fetching video metadata...")
        self.dur_lbl.setText("Duration: --:--")
        self.thumb_lbl.setText("Loading...")

        self.meta_thread = FetchMetadataThread(url)
        self.meta_thread.info_ready.connect(self._on_meta_ready)
        self.meta_thread.failed.connect(self._on_meta_failed)
        self.meta_thread.start()

    def _on_meta_ready(self, info: dict):
        self.btn_fetch.setEnabled(True)
        self.btn_fetch.setText("Get Information")
        self.title_lbl.setText(info.get('title', 'Unknown Title'))
        self.dur_lbl.setText(f"Duration: {info.get('duration_str', '--:--')}")

        thumb_url = info.get('thumbnail')
        if thumb_url:
            req = QNetworkRequest(QUrl(thumb_url))
            self.net_manager.get(req)

    def _on_thumbnail_downloaded(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            img = QImage()
            if img.loadFromData(data):
                pix = QPixmap.fromImage(img)
                scaled = pix.scaled(160, 90, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.thumb_lbl.setPixmap(scaled)
        reply.deleteLater()

    def _on_meta_failed(self, err: str):
        self.btn_fetch.setEnabled(True)
        self.btn_fetch.setText("Get Information")
        self.title_lbl.setText("Failed to fetch metadata.")
        self.thumb_lbl.setText("No Image")
        QMessageBox.critical(self, "Fetch Error", f"Could not fetch YouTube video info:\n{err}")

    def _on_download_clicked(self):
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Empty URL", "Please enter a valid YouTube URL.")
            return

        out_folder = self.out_edit.text().strip()
        if not out_folder:
            QMessageBox.warning(self, "Missing Folder", "Please select an output folder.")
            return

        mode = "audio" if self.mode_combo.currentText() == "Audio Only" else "video"
        quality = self.quality_combo.currentText()
        fmt = self.fmt_combo.currentText()

        self.btn_download.setEnabled(False)
        self.btn_cancel.show()
        self.btn_open_loc.hide()
        self.prog_bar.setValue(0)
        self.status_lbl.setText("Starting download...")

        self.download_thread = DownloadVideoThread(
            url=url,
            output_folder=out_folder,
            mode=mode,
            quality=quality,
            fmt=fmt,
            ffmpeg_path=self.ffmpeg_path
        )
        self.download_thread.progress.connect(self._on_download_progress)
        self.download_thread.completed.connect(self._on_download_completed)
        self.download_thread.failed.connect(self._on_download_failed)
        self.download_thread.start()

    def _on_download_progress(self, pct: float, status: str, speed: str, eta: str):
        self.prog_bar.setValue(int(pct))
        self.status_lbl.setText(status)
        self.speed_lbl.setText(f"Speed: {speed} | ETA: {eta}")

    def _on_download_completed(self, filepath: str):
        self.btn_download.setEnabled(True)
        self.btn_cancel.hide()
        self.btn_open_loc.show()
        self.last_output_path = filepath
        self.status_lbl.setText("✓ Download Completed!")
        self.speed_lbl.setText("")
        QMessageBox.information(self, "Success", f"Download complete!\nSaved to: {filepath}")

    def _on_download_failed(self, err: str):
        self.btn_download.setEnabled(True)
        self.btn_cancel.hide()
        self.status_lbl.setText("Download failed / cancelled.")
        self.speed_lbl.setText("")
        if "cancelled" not in err.lower():
            QMessageBox.critical(self, "Download Error", f"Download failed: {err}")

    def _on_cancel_clicked(self):
        if self.download_thread:
            self.download_thread.cancel()
            self.status_lbl.setText("Cancelling download...")

    def _on_open_location_clicked(self):
        if self.last_output_path and os.path.exists(self.last_output_path):
            folder = os.path.dirname(self.last_output_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        else:
            folder = self.out_edit.text().strip()
            if os.path.exists(folder):
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
