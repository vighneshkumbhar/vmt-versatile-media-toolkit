"""
main_window.py
The central MainWindow that hosts all panels and orchestrates the application.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSplitter, QStackedWidget, QProgressBar,
    QFileDialog, QMessageBox, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QIcon, QColor, QPixmap

try:
    from extensions.registry import ExtensionRegistry
    from extensions.loader import ExtensionLoader
    from extensions.lifecycle import ExtensionLifecycle
    _EXTENSIONS_AVAILABLE = True
except ImportError:
    _EXTENSIONS_AVAILABLE = False

import core.settings as settings
from core.ffmpeg_finder import find_ffmpeg, find_ffprobe, detect_hardware_encoders
from core.ffprobe_info import probe, MediaInfo
from core.job import Job, JobStatus
from core.job_queue import JobQueue
from core.presets import format_to_extension, VIDEO_FORMATS, AUDIO_FORMATS
from utils.file_utils import safe_output_path, human_size
from ui.styles import COLORS as C
from ui.drop_zone import DropZone
from ui.file_list import FileList
from ui.preview_panel import MediaPreviewPanel
from ui.queue_panel import QueuePanel
from ui.log_panel import LogPanel
from ui.pages.convert_page import ConvertPage
from ui.pages.compress_page import CompressPage
from ui.pages.resize_page import ResizePage
from ui.pages.audio_page import AudioPage
from ui.pages.gif_page import GifPage
from ui.pages.more_page import MorePage
from ui.pages.advanced_page import AdvancedPage
from ui.pages.extensions_page import ExtensionsPage
from ui.telemetry_widget import TelemetryHeroCard


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self):
        super().__init__()
        settings.load()

        self._ffmpeg_path: str = ""
        self._ffprobe_path: str = ""
        self._hw_encoders: dict[str, bool] = {}
        self._media_infos: dict[str, MediaInfo] = {}
        self._selected_file: Optional[str] = ""
        self._current_page_id: str = "convert"
        self._nav_btns: dict[str, QPushButton] = {}
        self._pages: dict = {}

        self._ext_registry: Optional["ExtensionRegistry"] = None
        self._ext_loader: Optional["ExtensionLoader"] = None
        self._ext_lifecycle: Optional["ExtensionLifecycle"] = None
        self._active_extension_instances: dict[str, object] = {}
        self._ext_pages: dict[str, list[str]] = {}  # ext_id -> page ids
        self._extensions_section_label: Optional[QLabel] = None
        self._ext_manager_window = None

        self.setWindowTitle("VMT — Versatile Media Toolkit  [Beta]")
        self.setMinimumSize(1100, 720)

        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "runner_icon.png"))
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self._restore_geometry()

        self._build_ui()
        self._load_extension_pages()
        self._load_initial_sample_media()
        self._discover_ffmpeg()

    # ── UI Construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = self._build_sidebar()
        root.addWidget(sidebar)

        # Main content column
        main_col = QWidget()
        main_col.setStyleSheet(f"background: {C['bg_base']};")
        main_col_lay = QVBoxLayout(main_col)
        main_col_lay.setContentsMargins(0, 0, 0, 0)
        main_col_lay.setSpacing(0)

        # Top header
        header = self._build_header()
        main_col_lay.addWidget(header)

        # Telemetry Hero Telemetry Card
        self._telemetry_card = TelemetryHeroCard()
        main_col_lay.addWidget(self._telemetry_card)

        # Body splitter: left (files) | right (operation)
        body_splitter = QSplitter(Qt.Horizontal)
        body_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {C['border']};
                width: 1px;
            }}
        """)

        # Left: file area
        file_area = self._build_file_area()
        body_splitter.addWidget(file_area)

        # Right: operation area
        op_area = self._build_operation_area()
        body_splitter.addWidget(op_area)

        body_splitter.setSizes([420, 620])
        body_splitter.setCollapsible(0, False)
        body_splitter.setCollapsible(1, False)

        # Main vertical splitter: Workspace (top) | Queue Panel & Log (bottom)
        v_splitter = QSplitter(Qt.Vertical)
        v_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {C['border']};
                height: 1px;
            }}
        """)
        v_splitter.addWidget(body_splitter)

        # Bottom container: Queue panel + Log panel
        bottom_container = QWidget()
        bottom_container.setStyleSheet(f"background: {C['bg_base']};")
        bottom_lay = QVBoxLayout(bottom_container)
        bottom_lay.setContentsMargins(0, 0, 0, 0)
        bottom_lay.setSpacing(0)

        # Queue panel
        self._queue_panel = QueuePanel()
        self._queue_panel.setMinimumHeight(140)
        self._queue_panel.start_requested.connect(self._start_queue)
        self._queue_panel.cancel_requested.connect(self._cancel_current)
        self._queue_panel.cancel_all_requested.connect(self._cancel_all)
        self._queue_panel.retry_requested.connect(self._retry_job)
        self._queue_panel.clear_completed.connect(self._clear_completed)
        self._queue_panel.show_log.connect(self._show_job_log)
        bottom_lay.addWidget(self._queue_panel, 1)

        # Log panel
        self._log_panel = LogPanel()
        bottom_lay.addWidget(self._log_panel)

        v_splitter.addWidget(bottom_container)
        v_splitter.setSizes([440, 240])
        v_splitter.setCollapsible(0, False)
        v_splitter.setCollapsible(1, False)

        main_col_lay.addWidget(v_splitter, 1)

        root.addWidget(main_col, 1)

        # Job queue engine
        self._job_queue = JobQueue()
        self._job_queue.job_added.connect(self._on_job_added)
        self._job_queue.job_status_changed.connect(self._on_job_status_changed)
        self._job_queue.job_progress.connect(self._on_job_progress)
        self._job_queue.job_log_line.connect(self._on_log_line)
        self._job_queue.job_time_info.connect(self._on_time_info)
        self._job_queue.queue_started.connect(lambda: self._queue_panel.set_running(True))
        self._job_queue.queue_finished.connect(self._on_queue_finished)

    def _load_extension_pages(self) -> None:
        """Initialize extension system and load all enabled extensions."""
        if not _EXTENSIONS_AVAILABLE:
            return
        try:
            self._ext_registry = ExtensionRegistry()
            self._ext_registry.load_from_disk()
            self._ext_loader = ExtensionLoader()
            self._ext_lifecycle = ExtensionLifecycle(
                self._ext_registry, self._ext_loader, self
            )
            for record in self._ext_registry.list_enabled():
                try:
                    self._ext_lifecycle.enable(record.id)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(
                        f"Failed to load extension {record.id}: {e}"
                    )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Extension system failed to initialize: {e}")

    def _on_extension_changed(self, ext_id: str) -> None:
        """Called when an extension is installed/uninstalled/enabled/disabled.
        Refreshes the lifecycle state from the registry.
        """
        if not self._ext_registry:
            return
        self._ext_registry.load_from_disk()

    def register_extension_page(
        self,
        ext_id: str,
        page_id: str,
        label: str,
        widget_class: type,
        description: str = "",
    ) -> None:
        """Register an extension page in More Tools, with an optional pin."""
        if page_id in self._pages:
            return  # Already registered

        try:
            widget = widget_class()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                f"Extension {ext_id} failed to create page widget {page_id}: {e}"
            )
            return

        idx = self._page_stack.addWidget(widget)
        self._pages[page_id] = (widget, idx)
        self._ext_pages.setdefault(ext_id, []).append(page_id)
        self._PAGE_INFO[page_id] = (label.strip(), description or f"Extension: {ext_id}")
        record = self._ext_registry.get(ext_id) if self._ext_registry else None
        pinned = bool(record and record.pinned)
        self._more_page.register_extension(page_id, label.strip(), description, pinned)
        if pinned:
            self._add_extension_shortcut(page_id, label)

    def _add_extension_shortcut(self, page_id: str, label: str) -> None:
        """Add a sidebar shortcut only for a user-pinned extension."""
        if page_id in self._nav_btns:
            return
        btn = QPushButton(label)
        btn.setFixedHeight(40)
        btn.clicked.connect(lambda checked=False, p=page_id: self._switch_page(p))
        self._nav_btns[page_id] = btn
        layout = self._sidebar.layout()
        insert_at = next((i for i in range(layout.count()) if layout.itemAt(i).spacerItem()), layout.count())
        if self._extensions_section_label is None:
            self._extensions_section_label = QLabel("PINNED EXTENSIONS")
            self._extensions_section_label.setStyleSheet(
                f"color: {C['text_dim']}; font-size: 10px; font-weight: 700; "
                "letter-spacing: 1px; padding: 10px 8px 2px 8px; background: transparent;"
            )
            layout.insertWidget(insert_at, self._extensions_section_label)
            insert_at += 1
        layout.insertWidget(insert_at, btn)

    def _set_extension_pinned(self, page_id: str, pinned: bool) -> None:
        ext_id = next((key for key, pages in self._ext_pages.items() if page_id in pages), None)
        if not ext_id:
            return
        registry = self._ext_registry
        record = registry.get(ext_id) if registry else None
        if record is None:
            registry = ExtensionRegistry()
            registry.load_from_disk()
            record = registry.get(ext_id)
        if record is None:
            return
        record.pinned = pinned
        registry.save_to_disk()
        self._more_page.set_extension_pinned(page_id, pinned)
        if pinned:
            self._add_extension_shortcut(page_id, record.name)
        elif page_id in self._nav_btns:
            self._nav_btns.pop(page_id).deleteLater()
        if not any(page in self._nav_btns for pages in self._ext_pages.values() for page in pages):
            if self._extensions_section_label is not None:
                self._extensions_section_label.deleteLater()
                self._extensions_section_label = None

    def unregister_extension_pages(self, ext_id: str) -> None:
        """Remove all pages registered by a given extension."""
        for page_id in self._ext_pages.pop(ext_id, []):
            self._more_page.unregister_extension(page_id)
            if page_id in self._pages:
                widget, _ = self._pages.pop(page_id)
                self._page_stack.removeWidget(widget)
                widget.deleteLater()
            if page_id in self._nav_btns:
                btn = self._nav_btns.pop(page_id)
                btn.deleteLater()
            self._PAGE_INFO.pop(page_id, None)

        if not self._ext_pages and self._extensions_section_label is not None:
            self._extensions_section_label.deleteLater()
            self._extensions_section_label = None

        if self._current_page_id not in self._pages:
            self._switch_page("convert")

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet(f"""
            QWidget {{
                background-color: {C['sidebar_bg']};
                border-right: 1px solid {C['border']};
            }}
        """)
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(12, 16, 12, 16)
        lay.setSpacing(4)

        # Logo area
        logo_frame = QWidget()
        logo_frame.setStyleSheet("background: transparent; border: none;")
        logo_lay = QVBoxLayout(logo_frame)
        logo_lay.setContentsMargins(4, 0, 4, 10)
        logo_lay.setSpacing(4)

        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "logo.png"))
        if os.path.exists(logo_path):
            logo_img_lbl = QLabel()
            pix = QPixmap(logo_path)
            logo_img_lbl.setPixmap(pix.scaledToWidth(160, Qt.SmoothTransformation))
            logo_img_lbl.setStyleSheet("background: transparent;")
            logo_lay.addWidget(logo_img_lbl)
        else:
            logo_text = QLabel("VMT")
            logo_text.setStyleSheet(f"""
                color: {C['text_primary']};
                font-size: 20px;
                font-weight: 800;
                background: transparent;
            """)
            logo_lay.addWidget(logo_text)

        logo_sub = QLabel("VERSATILE MEDIA TOOLKIT")
        logo_sub.setStyleSheet(f"""
            color: {C['text_dim']};
            font-size: 9px;
            font-weight: 800;
            letter-spacing: 1px;
            background: transparent;
            padding-left: 2px;
        """)
        logo_lay.addWidget(logo_sub)
        lay.addWidget(logo_frame)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {C['border']}; border: none; max-height: 1px;")
        lay.addWidget(sep)
        lay.addSpacing(6)

        # Nav buttons with pro icons
        nav_items = [
            ("convert",   "▶  Convert"),
            ("compress",  "🎬  Compress"),
            ("resize",    "📐  Resize"),
            ("audio",     "〰  Extract Audio"),
            ("gif",       "🎞  Make GIF"),
            ("more",      "🛠  More Tools"),
            ("extensions", "🧩  Extensions"),
        ]

        self._nav_btns: dict[str, QPushButton] = {}
        for page_id, label in nav_items:
            btn = QPushButton(label)
            btn.setFixedHeight(38)
            btn.clicked.connect(lambda checked, p=page_id: self._switch_page(p))
            self._nav_btns[page_id] = btn
            lay.addWidget(btn)

        lay.addStretch()

        # Advanced button
        advanced_btn = QPushButton(">_  Advanced")
        advanced_btn.setFixedHeight(38)
        advanced_btn.clicked.connect(lambda: self._switch_page("advanced"))
        self._nav_btns["advanced"] = advanced_btn
        lay.addWidget(advanced_btn)

        # Bottom: Status & VM Badge
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"background: {C['border']}; border: none; max-height: 1px;")
        lay.addWidget(sep2)
        lay.addSpacing(4)

        # FFmpeg status indicator
        self._ffmpeg_status_btn = QPushButton("● FFmpeg: searching…")
        self._ffmpeg_status_btn.setFixedHeight(28)
        self._ffmpeg_status_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {C['text_dim']};
                font-size: 11px;
                font-weight: 600;
                text-align: left;
                padding-left: 4px;
            }}
            QPushButton:hover {{
                color: {C['accent']};
            }}
        """)
        self._ffmpeg_status_btn.clicked.connect(self._locate_ffmpeg_manually)
        lay.addWidget(self._ffmpeg_status_btn)

        # Bottom VM Avatar Badge (Studio reference)
        vm_card = QFrame()
        vm_card.setStyleSheet(f"""
            background-color: #0E161C;
            border: 1px solid {C['border_card']};
            border-radius: 6px;
        """)
        vm_lay = QHBoxLayout(vm_card)
        vm_lay.setContentsMargins(6, 6, 8, 6)
        vm_lay.setSpacing(8)

        vm_badge = QLabel("VM")
        vm_badge.setFixedSize(26, 26)
        vm_badge.setAlignment(Qt.AlignCenter)
        vm_badge.setStyleSheet(f"""
            background-color: #17242D;
            color: {C['accent']};
            font-weight: 800;
            font-size: 10px;
            border-radius: 4px;
            border: 1px solid #1E333F;
        """)

        vm_text = QLabel("VMT Studio [Beta]")
        vm_text.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px; font-weight: 700; background: transparent;")

        vm_lay.addWidget(vm_badge)
        vm_lay.addWidget(vm_text)
        vm_lay.addStretch()
        lay.addWidget(vm_card)

        # Store nav btns reference
        self._sidebar = sidebar
        return sidebar

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet(f"""
            background: {C['bg_dark']};
            border-bottom: 1px solid {C['border']};
        """)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(24, 10, 24, 10)
        lay.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        self._page_subtitle = QLabel("CONVERSION QUEUE")
        self._page_subtitle.setStyleSheet(f"""
            color: {C['text_dim']};
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.4px;
            background: transparent;
        """)

        self._page_title = QLabel("Convert Media")
        self._page_title.setStyleSheet(f"""
            color: #FFFFFF;
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.3px;
            background: transparent;
        """)

        title_col.addWidget(self._page_subtitle)
        title_col.addWidget(self._page_title)
        lay.addLayout(title_col)

        lay.addStretch()

        # + ADD MEDIA Button
        self._add_media_btn = QPushButton("+ ADD MEDIA")
        self._add_media_btn.setProperty("class", "outline-accent")
        self._add_media_btn.setFixedHeight(34)
        self._add_media_btn.clicked.connect(self._add_media_dialog)
        lay.addWidget(self._add_media_btn)

        return header

    def _add_media_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Media Files",
            "",
            "Media Files (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.wmv *.mpeg *.mpg "
            "*.m4v *.ts *.m2ts *.3gp *.mp3 *.wav *.flac *.aac *.m4a *.ogg *.opus "
            "*.wma *.aiff *.gif);;"
            "All Files (*.*)"
        )
        if paths:
            self._add_files(paths)

    def _build_file_area(self) -> QWidget:
        area = QWidget()
        area.setStyleSheet(f"background: {C['bg_base']};")
        lay = QVBoxLayout(area)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        # Section title
        files_title = QLabel("FILES & PREVIEW")
        files_title.setStyleSheet(f"""
            color: {C['text_dim']};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
            background: transparent;
        """)
        lay.addWidget(files_title)

        # Drop zone (shown when list is empty)
        self._drop_zone = DropZone()
        self._drop_zone.files_dropped.connect(self._add_files)
        lay.addWidget(self._drop_zone)

        # File list (shown when files added)
        self._file_list = FileList()
        self._file_list.files_changed.connect(self._on_files_changed)
        self._file_list.file_selected.connect(self._on_file_selected)
        self._file_list.media_info_ready.connect(self._on_media_info_ready)
        self._file_list.hide()
        lay.addWidget(self._file_list, 1)

        # Media Preview Panel
        self._preview_panel = MediaPreviewPanel()
        self._preview_panel.details_requested.connect(self._on_preview_details_requested)
        lay.addWidget(self._preview_panel, 2)

        return area

    def _build_operation_area(self) -> QWidget:
        area = QWidget()
        area.setStyleSheet(f"background: {C['bg_base']};")
        lay = QVBoxLayout(area)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Operation pages (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        self._page_stack = QStackedWidget()
        self._page_stack.setStyleSheet("background: transparent;")

        self._convert_page = ConvertPage()
        self._compress_page = CompressPage()
        self._resize_page = ResizePage()
        self._audio_page = AudioPage()
        self._gif_page = GifPage()
        self._more_page = MorePage()
        self._more_page.extension_open_requested.connect(self._switch_page)
        self._more_page.extension_pin_requested.connect(self._set_extension_pinned)
        self._extensions_page = ExtensionsPage()
        self._extensions_page.extension_installed.connect(self._on_extension_changed)
        self._extensions_page.extension_uninstalled.connect(self._on_extension_changed)
        self._extensions_page.extension_enabled.connect(self._on_extension_changed)
        self._extensions_page.extension_disabled.connect(self._on_extension_changed)
        self._advanced_page = AdvancedPage()

        self._pages = {
            "convert":  (self._convert_page,  0),
            "compress": (self._compress_page, 1),
            "resize":   (self._resize_page,   2),
            "audio":    (self._audio_page,    3),
            "gif":      (self._gif_page,      4),
            "more":     (self._more_page,     5),
            "extensions": (self._extensions_page, 6),
            "advanced": (self._advanced_page, 7),
        }
        # Now safe to apply nav styling
        self._switch_page("convert")

        for page, _ in self._pages.values():
            self._page_stack.addWidget(page)

        scroll.setWidget(self._page_stack)
        lay.addWidget(scroll, 1)

        # Output folder row
        output_frame = QFrame()
        output_frame.setProperty("class", "card")
        output_lay = QHBoxLayout(output_frame)
        output_lay.setContentsMargins(16, 12, 16, 12)
        output_lay.setSpacing(10)

        folder_icon = QLabel("📁")
        folder_icon.setStyleSheet("background: transparent; font-size: 16px;")
        folder_label = QLabel("Output:")
        folder_label.setStyleSheet(f"color: {C['text_muted']}; background: transparent;")
        folder_label.setFixedWidth(56)

        self._output_folder_label = QLabel(settings.get_output_folder())
        self._output_folder_label.setStyleSheet(f"color: {C['text_primary']}; background: transparent; font-size: 12px;")
        self._output_folder_label.setToolTip(settings.get_output_folder())

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedHeight(30)
        browse_btn.setFixedWidth(70)
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg_card_alt']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                color: {C['text_muted']};
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {C['bg_hover']};
                color: white;
            }}
        """)
        browse_btn.clicked.connect(self._browse_output_folder)

        output_lay.addWidget(folder_icon)
        output_lay.addWidget(folder_label)
        output_lay.addWidget(self._output_folder_label, 1)
        output_lay.addWidget(browse_btn)

        # START button
        self._start_btn = QPushButton("▶  START")
        self._start_btn.setProperty("class", "primary")
        self._start_btn.setFixedHeight(50)
        self._start_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C['accent']}, stop:1 {C['accent_light']});
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C['accent_dark']}, stop:1 {C['accent']});
            }}
            QPushButton:disabled {{
                background: {C['bg_card']};
                color: {C['text_dim']};
            }}
        """)
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start_clicked)

        lay.addWidget(output_frame)
        lay.addWidget(self._start_btn)

        return area

    # ── FFmpeg Discovery ──────────────────────────────────────────────────────

    def _discover_ffmpeg(self) -> None:
        self._ffmpeg_path = settings.get("ffmpeg_path") or ""
        self._ffprobe_path = settings.get("ffprobe_path") or ""

        # Try to find if paths are missing or invalid
        if not self._ffmpeg_path or not os.path.exists(self._ffmpeg_path):
            from core.ffmpeg_finder import find_ffmpeg
            self._ffmpeg_path = find_ffmpeg() or ""
        if not self._ffprobe_path or not os.path.exists(self._ffprobe_path):
            from core.ffmpeg_finder import find_ffprobe
            self._ffprobe_path = find_ffprobe() or ""

        self._job_queue.set_ffmpeg_path(self._ffmpeg_path)
        self._file_list.set_ffprobe_path(self._ffprobe_path)

        if self._ffmpeg_path:
            self._ffmpeg_status_btn.setText(f"● FFmpeg: found")
            self._ffmpeg_status_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {C['success']};
                    font-size: 11px;
                    text-align: left;
                    padding-left: 8px;
                }}
                QPushButton:hover {{ color: white; }}
            """)
            # Detect hardware encoders in background
            QTimer.singleShot(500, self._detect_hw_encoders)
        else:
            self._ffmpeg_status_btn.setText("⚠ FFmpeg: not found")
            self._ffmpeg_status_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {C['warning']};
                    font-size: 11px;
                    text-align: left;
                    padding-left: 8px;
                }}
                QPushButton:hover {{ color: white; }}
            """)
            QTimer.singleShot(300, self._show_ffmpeg_missing_banner)

    def _detect_hw_encoders(self) -> None:
        if not self._ffmpeg_path:
            return
        thread = _HWDetectThread(self._ffmpeg_path, self)
        thread.result.connect(self._on_hw_detected)
        thread.start()
        self._hw_thread = thread

    def _on_hw_detected(self, encoders: dict) -> None:
        self._hw_encoders = encoders
        self._advanced_page.update_hw_encoders(encoders)
        if hasattr(self, "_telemetry_card"):
            if encoders.get('nvenc'):
                self._telemetry_card.set_hw_encoder_name("NVIDIA NVENC")
            elif encoders.get('qsv'):
                self._telemetry_card.set_hw_encoder_name("Intel QSV")
            elif encoders.get('amf'):
                self._telemetry_card.set_hw_encoder_name("AMD AMF")
            else:
                self._telemetry_card.set_hw_encoder_name("CPU Multi-Thread")

    def _show_ffmpeg_missing_banner(self) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle("FFmpeg Not Found")
        msg.setIcon(QMessageBox.Warning)
        msg.setText(
            "<b>FFmpeg was not found.</b>"
        )
        msg.setInformativeText(
            "VMT needs FFmpeg to process media files.\n\n"
            "To fix this:\n"
            "  • Place <b>ffmpeg.exe</b> in the <b>bin/</b> folder next to this app\n"
            "  • Or install FFmpeg and add it to your PATH\n\n"
            "Click 'Locate FFmpeg' to browse for the executable."
        )
        locate_btn = msg.addButton("Locate FFmpeg…", QMessageBox.ActionRole)
        msg.addButton("Close", QMessageBox.RejectRole)
        msg.exec()
        if msg.clickedButton() == locate_btn:
            self._locate_ffmpeg_manually()

    def _locate_ffmpeg_manually(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Locate ffmpeg.exe", "", "Executable (ffmpeg.exe ffmpeg)")
        if path and os.path.exists(path):
            self._ffmpeg_path = path
            self._job_queue.set_ffmpeg_path(path)
            settings.set("ffmpeg_path", path)
            settings.save()
            self._ffmpeg_status_btn.setText("● FFmpeg: found")
            self._ffmpeg_status_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {C['success']};
                    font-size: 11px;
                    text-align: left;
                    padding-left: 8px;
                }}
            """)
            # Also find ffprobe next to it
            ffprobe_candidate = os.path.join(os.path.dirname(path), "ffprobe.exe")
            if os.path.exists(ffprobe_candidate):
                self._ffprobe_path = ffprobe_candidate
                self._file_list.set_ffprobe_path(ffprobe_candidate)
                settings.set("ffprobe_path", ffprobe_candidate)
                settings.save()
            self._update_start_button()
            QTimer.singleShot(300, self._detect_hw_encoders)

    # ── Navigation ─────────────────────────────────────────────────────────────

    _PAGE_INFO = {
        "convert":  ("Convert",       "Change your media files to a different format"),
        "compress": ("Compress",      "Make your video files smaller"),
        "resize":   ("Resize",        "Change the video resolution"),
        "audio":    ("Extract Audio", "Pull the audio track from any video"),
        "gif":      ("Make GIF",      "Turn a video clip into an animated GIF"),
        "more":     ("More Tools",    "Remove audio, extract frames, view media info"),
        "extensions": ("Extensions",  "Browse, install and manage extensions"),
        "advanced": ("Advanced",      "Detailed FFmpeg settings for experienced users"),
    }

    def open_extension_manager(self) -> None:
        if getattr(self, "_ext_manager_window", None) is not None:
            try:
                if self._ext_manager_window.isVisible():
                    self._ext_manager_window.show()
                    self._ext_manager_window.raise_()
                    self._ext_manager_window.activateWindow()
                    return
            except RuntimeError:
                self._ext_manager_window = None

        from ui.extension_manager_window import ExtensionManagerWindow
        self._ext_manager_window = ExtensionManagerWindow(parent=self)
        self._ext_manager_window.extension_changed.connect(self._on_extension_changed)
        self._ext_manager_window.show()

    def _switch_page(self, page_id: str, init: bool = False) -> None:
        if page_id == "extensions":
            self.open_extension_manager()
            return

        if page_id in self._pages:
            _, idx = self._pages[page_id]
            self._page_stack.setCurrentIndex(idx)

        info = self._PAGE_INFO.get(page_id, (page_id.title(), ""))
        self._page_title.setText(info[0])

        for pid, btn in self._nav_btns.items():
            if pid == page_id:
                btn.setProperty("class", "nav-active")
            else:
                btn.setProperty("class", "nav")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self._current_page_id = page_id

    # ── Sample Video & Media Preview Helpers ────────────────────────────────────

    def _get_sample_video_path(self) -> str:
        candidates = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sample_video.mp4")),
            os.path.abspath(os.path.join(os.getcwd(), "assets", "sample_video.mp4")),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return ""

    def _load_initial_sample_media(self) -> None:
        sample_path = self._get_sample_video_path()
        if sample_path:
            self._preview_panel.load_media(sample_path, is_sample=True)

    def _on_preview_details_requested(self, path: str) -> None:
        self._switch_page("more")
        if hasattr(self, "_more_page"):
            self._more_page._switch_tool("media_info")
            info = self._media_infos.get(path)
            if info:
                self._more_page.media_info_panel.update_info(info)

    def closeEvent(self, event) -> None:
        if hasattr(self, "_preview_panel"):
            self._preview_panel._stop_playback()
        super().closeEvent(event)

    # ── File Management ────────────────────────────────────────────────────────

    def _add_files(self, paths: list[str]) -> None:
        self._file_list.add_files(paths)

    def _on_files_changed(self) -> None:
        has_files = self._file_list.count > 0
        self._drop_zone.setVisible(not has_files)
        self._file_list.setVisible(has_files)
        self._update_start_button()

        if has_files:
            # If user has files, pick selected file or first file
            selected = self._file_list.selected_file or (self._file_list.file_paths[0] if self._file_list.file_paths else "")
            if selected:
                self._on_file_selected(selected)
        else:
            self._selected_file = ""
            sample_path = self._get_sample_video_path()
            if sample_path:
                self._preview_panel.load_media(sample_path, is_sample=True)
            else:
                self._preview_panel.clear()

    def _on_file_selected(self, path: str) -> None:
        self._selected_file = path
        if path:
            self._preview_panel.load_media(path, is_sample=False)
        info = self._media_infos.get(path)
        if info:
            self._more_page.media_info_panel.update_info(info)

    def _on_media_info_ready(self, path: str, info: object) -> None:
        self._media_infos[path] = info
        if path == self._selected_file:
            self._more_page.media_info_panel.update_info(info)

    def _update_start_button(self) -> None:
        can_start = (
            self._file_list.count > 0 and
            bool(self._ffmpeg_path) and
            not self._job_queue.is_running
        )
        self._start_btn.setEnabled(can_start)

    # ── Output folder ──────────────────────────────────────────────────────────

    def _browse_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Choose Output Folder", settings.get_output_folder())
        if folder:
            settings.set("output_folder", folder)
            settings.save()
            self._output_folder_label.setText(folder)
            self._output_folder_label.setToolTip(folder)

    # ── Job Building ──────────────────────────────────────────────────────────

    def _on_start_clicked(self) -> None:
        if not self._ffmpeg_path:
            self._show_ffmpeg_missing_banner()
            return

        files = self._file_list.file_paths
        if not files:
            return

        page_id = getattr(self, "_current_page_id", "convert")

        # Don't add duplicate waiting jobs for the same files
        existing_input = {j.input_file for j in self._job_queue.jobs
                         if j.status == JobStatus.WAITING}

        added = 0
        for f in files:
            if f in existing_input:
                continue
            job = self._build_job(f, page_id)
            if job:
                self._job_queue.add_job(job)
                added += 1

        if added == 0:
            QMessageBox.information(self, "No New Jobs",
                "All selected files are already in the queue.")
            return

        if not self._job_queue.is_running:
            self._job_queue.start()

    def _build_job(self, input_file: str, page_id: str) -> Optional[Job]:
        """Construct a Job for the given file and current page settings."""
        output_folder = settings.get_output_folder()
        os.makedirs(output_folder, exist_ok=True)
        overwrite = settings.get("overwrite_files", False)
        hw_enc = self._get_active_hw_encoder()

        try:
            if page_id == "convert":
                fmt = self._convert_page.output_format
                ext = format_to_extension(fmt)
                output = safe_output_path(input_file, output_folder, ext, "_converted", overwrite)
                args = self._convert_page.build_ffmpeg_args(input_file, output, hw_enc)
                desc = f"Convert → {fmt}"

            elif page_id == "compress":
                fmt = self._compress_page.output_format
                ext = format_to_extension(fmt)
                output = safe_output_path(input_file, output_folder, ext, "_compressed", overwrite)
                args = self._compress_page.build_ffmpeg_args(input_file, output, hw_enc)
                desc = f"Compress → {fmt}"

            elif page_id == "resize":
                fmt = self._resize_page.output_format
                ext = format_to_extension(fmt)
                output = safe_output_path(input_file, output_folder, ext, "_resized", overwrite)
                args = self._resize_page.build_ffmpeg_args(input_file, output, hw_enc)
                res = self._resize_page.resolution
                desc = f"Resize → {res[1]}p" if res else "Resize"

            elif page_id == "audio":
                fmt = self._audio_page.output_format
                ext = format_to_extension(fmt)
                output = safe_output_path(input_file, output_folder, ext, "_audio", overwrite)
                args = self._audio_page.build_ffmpeg_args(input_file, output)
                desc = f"Extract Audio → {fmt}"

            elif page_id == "gif":
                output = safe_output_path(input_file, output_folder, "gif", "_animated", overwrite)
                args = self._gif_page.build_ffmpeg_args(input_file, output)
                desc = "Make GIF"

            elif page_id == "more":
                tool = self._more_page.active_tool
                if tool == "media_info":
                    return None  # Not a processing operation
                ext = self._more_page.get_output_extension()
                suffix = self._more_page.get_operation_suffix()
                output = safe_output_path(input_file, output_folder, ext, suffix, overwrite)
                args = self._more_page.build_ffmpeg_args(input_file, output)
                desc = {
                    "remove_audio": "Remove Audio",
                    "extract_frame": "Extract Frame",
                }.get(tool, "Process")

            elif page_id == "advanced":
                # Advanced page builds on top of convert
                fmt = self._convert_page.output_format
                ext = format_to_extension(fmt)
                output = safe_output_path(input_file, output_folder, ext, "_output", overwrite)
                base_args = self._convert_page.build_ffmpeg_args(input_file, output, hw_enc)
                extra = self._advanced_page.get_extra_args()
                # Insert extra args before output file
                base_args = base_args[:-1] + extra + [base_args[-1]]
                args = base_args
                desc = "Advanced → " + fmt

            else:
                return None

            # Get duration for progress calculation
            duration = 0.0
            if input_file in self._media_infos:
                duration = self._media_infos[input_file].duration

            job = Job(
                input_file=input_file,
                output_file=output,
                ffmpeg_args=args,
                operation=page_id,
                description=desc,
                duration=duration,
            )
            return job

        except Exception as e:
            QMessageBox.critical(self, "Build Error",
                f"Failed to prepare job for:\n{os.path.basename(input_file)}\n\n{e}")
            return None

    def _get_active_hw_encoder(self) -> Optional[str]:
        # Use hw encoder only if explicitly chosen (future: toggle in advanced page)
        return None

    # ── Queue Callbacks ────────────────────────────────────────────────────────

    def _on_job_added(self, job: Job) -> None:
        self._queue_panel.add_job_row(job)
        self._log_panel.clear_for_job(job.id)

    def _on_job_status_changed(self, job_id: str, status: JobStatus) -> None:
        self._queue_panel.update_job_status(job_id, status)

        if status == JobStatus.RUNNING:
            # Find the job to get its command
            for j in self._job_queue.jobs:
                if j.id == job_id:
                    self._log_panel.set_job_command(job_id, j.ffmpeg_command)
                    self._running_label.setText(f"Processing: {j.input_name}")
                    self._header_progress.show()
                    break

        elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            if status == JobStatus.FAILED:
                for j in self._job_queue.jobs:
                    if j.id == job_id and j.error_message:
                        self._show_job_error(j)
                        break

        self._update_overall_progress()

    def _show_job_error(self, job: Job) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle("Conversion Failed")
        msg.setIcon(QMessageBox.Critical)
        msg.setText(f"<b>Failed:</b> {job.input_name}")
        msg.setInformativeText(
            f"{job.error_message}\n\n"
            "The remaining files will continue processing."
        )
        show_log_btn = msg.addButton("Show Details", QMessageBox.ActionRole)
        msg.addButton("Close", QMessageBox.RejectRole)
        msg.exec()
        if msg.clickedButton() == show_log_btn:
            self._show_job_log(job.id)

    def _on_job_progress(self, job_id: str, pct: float) -> None:
        self._queue_panel.update_job_progress(job_id, pct)
        self._header_progress.setValue(int(pct))
        self._update_overall_progress()

    def _on_log_line(self, job_id: str, line: str) -> None:
        self._log_panel.append_log_line(job_id, line)

    def _on_time_info(self, job_id: str, elapsed: float, eta: float, pos: float) -> None:
        from utils.time_utils import format_eta
        eta_str = format_eta(eta) if eta > 0 else "…"
        self._running_label.setText(f"ETA: {eta_str}")

    def _on_queue_finished(self) -> None:
        self._queue_panel.set_running(False)
        self._header_progress.hide()
        self._header_progress.setValue(0)
        self._running_label.setText("")
        self._update_start_button()
        self._update_overall_progress()

    def _update_overall_progress(self) -> None:
        total = self._job_queue.total_count
        done = self._job_queue.completed_count
        failed = self._job_queue.failed_count
        pct = self._job_queue.overall_progress
        self._queue_panel.set_overall_progress(done + failed, total, pct)

        if total > 0:
            status = f"{done}/{total} completed"
            if failed > 0:
                status += f" ({failed} failed)"
            self._queue_panel.set_status(status)
        else:
            self._queue_panel.set_status("Ready")

    def _start_queue(self) -> None:
        if not self._job_queue.is_running:
            self._job_queue.start()

    def _cancel_current(self) -> None:
        self._job_queue.cancel_current()

    def _cancel_all(self) -> None:
        self._job_queue.cancel_all()

    def _retry_job(self, job_id: str) -> None:
        self._job_queue.retry_job(job_id)
        if not self._job_queue.is_running:
            self._job_queue.start()

    def _clear_completed(self) -> None:
        self._job_queue.clear_completed()
        self._queue_panel.clear_all_rows()
        # Re-add non-cleared jobs
        for job in self._job_queue.jobs:
            self._queue_panel.add_job_row(job)
            self._queue_panel.update_job_status(job.id, job.status)
        self._update_overall_progress()

    def _show_job_log(self, job_id: str) -> None:
        self._log_panel.show_job_log(job_id)

    # ── Window persistence ────────────────────────────────────────────────────

    def _restore_geometry(self) -> None:
        w = settings.get("window_width", 1150)
        h = settings.get("window_height", 750)
        x = settings.get("window_x", -1)
        y = settings.get("window_y", -1)
        self.resize(w, h)
        if x >= 0 and y >= 0:
            self.move(x, y)

    def closeEvent(self, event) -> None:
        geo = self.geometry()
        settings.set("window_width", geo.width())
        settings.set("window_height", geo.height())
        settings.set("window_x", geo.x())
        settings.set("window_y", geo.y())
        settings.save()

        if self._job_queue.is_running:
            reply = QMessageBox.question(
                self, "Quit",
                "A conversion is in progress. Quit anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                event.ignore()
                return
            self._job_queue.cancel_all()

        event.accept()

    # ── Extensions Integration Stubs ──────────────────────────────────────────
    
    def _on_extension_changed(self, ext_id: str) -> None:
        """Synchronize the persistent registry after Extension Manager actions."""
        if self._ext_registry is not None:
            self._ext_registry.load_from_disk()

    def _load_extension_pages(self) -> None:
        """Load every enabled persisted extension once the host UI is ready."""
        if not _EXTENSIONS_AVAILABLE:
            return
        try:
            self._ext_registry = ExtensionRegistry()
            self._ext_registry.load_from_disk()
            self._ext_loader = ExtensionLoader()
            self._ext_lifecycle = ExtensionLifecycle(
                self._ext_registry, self._ext_loader, self
            )
            for record in self._ext_registry.list_enabled():
                self._ext_lifecycle.enable(record.id)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("Extension startup failed: %s", exc, exc_info=True)


class _HWDetectThread(QThread):
    result = Signal(dict)

    def __init__(self, ffmpeg_path: str, parent=None):
        super().__init__(parent)
        self._ffmpeg_path = ffmpeg_path

    def run(self) -> None:
        encoders = detect_hardware_encoders(self._ffmpeg_path)
        self.result.emit(encoders)
