"""
queue_panel.py
Modern high-precision job queue panel matching the Studio Obsidian & Cyber Mint design.
Features structured columns: JOB (File + Meta), OUTPUT, PROGRESS, and actions.
"""
from __future__ import annotations
import os
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from core.job import Job, JobStatus
from utils.time_utils import format_eta, seconds_to_hms
from ui.styles import COLORS as C


class JobRowWidget(QFrame):
    """
    Single row in the queue showing JOB (with film icon + metadata), OUTPUT format, and PROGRESS.
    """

    retry_requested = Signal(str)   # job_id
    remove_requested = Signal(str)  # job_id
    details_requested = Signal(str) # job_id

    STATUS_STYLE = {
        JobStatus.WAITING:   (C['text_dim'],    "○  Waiting"),
        JobStatus.RUNNING:   (C['accent'],      "▶  Encoding"),
        JobStatus.COMPLETED: (C['success'],     "✓  Ready"),
        JobStatus.FAILED:    (C['error'],       "✗  Failed"),
        JobStatus.CANCELLED: (C['warning'],     "⊘  Cancelled"),
    }

    def __init__(self, job: Job, parent=None):
        super().__init__(parent)
        self._job = job
        self.setFixedHeight(64)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border-bottom: 1px solid {C['border']};
            }}
            QFrame:hover {{
                background-color: {C['bg_hover']};
            }}
        """)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(16)

        # ── 1. Media Icon ──────────────────────────────────────────
        icon_box = QFrame()
        icon_box.setFixedSize(36, 36)
        icon_box.setStyleSheet(f"""
            background-color: {C['bg_card']};
            border: 1px solid {C['border_card']};
            border-radius: 6px;
        """)
        icon_box_lay = QVBoxLayout(icon_box)
        icon_box_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("🎬")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 16px; background: transparent;")
        icon_box_lay.addWidget(icon_lbl)
        layout.addWidget(icon_box)

        # ── 2. Job File Info (Title + Metadata) ────────────────────
        job_col = QVBoxLayout()
        job_col.setSpacing(2)
        job_col.setContentsMargins(0, 2, 0, 2)

        self._input_label = QLabel(self._job.input_name)
        self._input_label.setStyleSheet(f"""
            color: #FFFFFF;
            font-size: 13px;
            font-weight: 700;
            background: transparent;
        """)
        self._input_label.setMaximumWidth(280)

        # Build clean technical metadata
        meta_str = self._job.description or "Source Stream"
        if not meta_str.startswith("→"):
            meta_str = f"FFmpeg Stream · {meta_str}"
        self._meta_label = QLabel(meta_str)
        self._meta_label.setStyleSheet(f"""
            color: {C['text_muted']};
            font-size: 11px;
            font-weight: 500;
            background: transparent;
        """)
        self._meta_label.setMaximumWidth(280)

        job_col.addWidget(self._input_label)
        job_col.addWidget(self._meta_label)
        layout.addLayout(job_col, 2)

        # ── 3. Output Format Badge ─────────────────────────────────
        out_col = QVBoxLayout()
        out_col.setAlignment(Qt.AlignVCenter)
        
        # Extract output extension / format name
        out_ext = os.path.splitext(self._job.output_path)[1].upper().replace(".", "") or "MP4"
        self._format_badge = QLabel(out_ext)
        self._format_badge.setAlignment(Qt.AlignCenter)
        self._format_badge.setFixedWidth(54)
        self._format_badge.setStyleSheet(f"""
            color: {C['accent']};
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 0.5px;
            background-color: {C['bg_card']};
            border: 1px solid {C['border_card']};
            border-radius: 4px;
            padding: 4px 6px;
        """)
        out_col.addWidget(self._format_badge)
        layout.addLayout(out_col, 1)

        # ── 4. Progress Bar & Percentage ───────────────────────────
        prog_col = QHBoxLayout()
        prog_col.setSpacing(10)
        prog_col.setAlignment(Qt.AlignVCenter)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(140)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setProperty("class", "thin")

        self._pct_label = QLabel("0%")
        self._pct_label.setFixedWidth(42)
        self._pct_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._pct_label.setStyleSheet(f"""
            color: {C['accent']};
            font-size: 11px;
            font-weight: 700;
            background: transparent;
        """)

        prog_col.addWidget(self._progress_bar)
        prog_col.addWidget(self._pct_label)
        layout.addLayout(prog_col, 2)

        # ── 5. Action Buttons ──────────────────────────────────────
        actions_lay = QHBoxLayout()
        actions_lay.setSpacing(6)

        self._retry_btn = QPushButton("Retry")
        self._retry_btn.setFixedHeight(26)
        self._retry_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {C['accent']};
                color: {C['accent']};
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                padding: 2px 8px;
            }}
            QPushButton:hover {{ background: {C['accent']}; color: #080C0E; }}
        """)
        self._retry_btn.clicked.connect(lambda: self.retry_requested.emit(self._job.id))
        self._retry_btn.hide()

        self._remove_btn = QPushButton("✕")
        self._remove_btn.setFixedSize(26, 26)
        self._remove_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {C['border']};
                color: {C['text_muted']};
                font-size: 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{ color: {C['error']}; border-color: {C['error']}; background: rgba(248,113,113,0.1); }}
        """)
        self._remove_btn.clicked.connect(lambda: self.remove_requested.emit(self._job.id))

        actions_lay.addWidget(self._retry_btn)
        actions_lay.addWidget(self._remove_btn)
        layout.addLayout(actions_lay)

    def update_status(self, status: JobStatus) -> None:
        if status == JobStatus.COMPLETED:
            self._progress_bar.setValue(100)
            self._pct_label.setText("100%")
            self._pct_label.setStyleSheet(f"color: {C['success']}; font-weight: 700; font-size: 11px;")
            self._retry_btn.hide()
            self._remove_btn.show()
        elif status == JobStatus.RUNNING:
            self._retry_btn.hide()
            self._remove_btn.hide()
        elif status in (JobStatus.FAILED, JobStatus.CANCELLED):
            self._pct_label.setText("Failed")
            self._pct_label.setStyleSheet(f"color: {C['error']}; font-weight: 700; font-size: 11px;")
            self._retry_btn.show()
            self._remove_btn.show()
        else:
            self._retry_btn.hide()
            self._remove_btn.show()

    def update_progress(self, pct: float) -> None:
        self._progress_bar.setValue(int(pct))
        self._pct_label.setText(f"{int(pct)}%")


class QueuePanel(QWidget):
    """
    The main queue panel displaying column headers, active jobs list, and control bar.
    """

    start_requested  = Signal()
    cancel_requested = Signal()
    cancel_all_requested = Signal()
    retry_requested  = Signal(str)
    clear_completed  = Signal()
    show_log         = Signal(str)   # job_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._job_rows: dict[str, JobRowWidget] = {}
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_overall)
        self._elapsed = 0
        self._total_jobs = 0
        self._done_jobs = 0
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Column Header Row ──────────────────────────────────────
        col_header = QFrame()
        col_header.setFixedHeight(34)
        col_header.setStyleSheet(f"""
            background-color: {C['bg_dark']};
            border-top: 1px solid {C['border']};
            border-bottom: 1px solid {C['border']};
        """)
        ch_lay = QHBoxLayout(col_header)
        ch_lay.setContentsMargins(20, 0, 20, 0)
        ch_lay.setSpacing(16)

        def make_col_lbl(text: str, stretch: int):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"""
                color: {C['text_dim']};
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 1px;
                background: transparent;
            """)
            ch_lay.addWidget(lbl, stretch)
            return lbl

        # Space for icon + Job title
        ch_lay.addSpacing(36)
        make_col_lbl("JOB", 2)
        make_col_lbl("OUTPUT", 1)
        make_col_lbl("PROGRESS", 2)
        ch_lay.addSpacing(60) # Actions space

        root.addWidget(col_header)

        # ── Scrollable list of job rows ────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet(f"background-color: {C['bg_base']}; border: none;")

        self._list_container = QWidget()
        self._list_container.setStyleSheet(f"background-color: {C['bg_base']};")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch()

        # Empty state label
        self._empty_label = QLabel("No active jobs in queue.\nAdd media files and select a task to start encoding.")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            color: {C['text_dim']};
            font-size: 12px;
            font-weight: 500;
            line-height: 1.5;
            padding: 30px;
            background: transparent;
        """)
        self._list_layout.addWidget(self._empty_label)

        self._scroll.setWidget(self._list_container)
        root.addWidget(self._scroll, 1)

        # ── Bottom Action & Telemetry Summary Bar ──────────────────
        footer = QFrame()
        footer.setFixedHeight(48)
        footer.setStyleSheet(f"""
            background-color: {C['bg_dark']};
            border-top: 1px solid {C['border']};
        """)
        foot_lay = QHBoxLayout(footer)
        foot_lay.setContentsMargins(16, 0, 16, 0)
        foot_lay.setSpacing(12)

        self._summary_label = QLabel("0 jobs in queue")
        self._summary_label.setStyleSheet(f"color: {C['text_muted']}; font-size: 12px; font-weight: 600;")
        foot_lay.addWidget(self._summary_label)

        foot_lay.addStretch()

        # HW Accel Indicator Tag
        hw_tag = QFrame()
        hw_tag.setStyleSheet(f"""
            background-color: #0E1A22;
            border: 1px solid #1E3744;
            border-radius: 4px;
            padding: 2px 8px;
        """)
        hw_tag_lay = QHBoxLayout(hw_tag)
        hw_tag_lay.setContentsMargins(4, 2, 4, 2)
        hw_tag_lay.setSpacing(4)
        bolt = QLabel("⚡")
        bolt.setStyleSheet("font-size: 11px; background: transparent;")
        hw_txt = QLabel("10x HW ACCEL")
        hw_txt.setStyleSheet(f"color: {C['accent']}; font-size: 10px; font-weight: 800; letter-spacing: 0.8px; background: transparent;")
        hw_tag_lay.addWidget(bolt)
        hw_tag_lay.addWidget(hw_txt)
        foot_lay.addWidget(hw_tag)

        self._clear_btn = QPushButton("Clear Done")
        self._clear_btn.setFixedHeight(28)
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg_card']};
                border: 1px solid {C['border_card']};
                color: {C['text_muted']};
                border-radius: 4px;
                font-size: 11px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{ color: #FFFFFF; background: {C['bg_hover']}; }}
        """)
        self._clear_btn.clicked.connect(self.clear_completed.emit)
        foot_lay.addWidget(self._clear_btn)

        self._cancel_all_btn = QPushButton("Cancel All")
        self._cancel_all_btn.setFixedHeight(28)
        self._cancel_all_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {C['border_card']};
                color: {C['error']};
                border-radius: 4px;
                font-size: 11px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{ background: rgba(248,113,113,0.15); }}
        """)
        self._cancel_all_btn.clicked.connect(self.cancel_all_requested.emit)
        self._cancel_all_btn.hide()
        foot_lay.addWidget(self._cancel_all_btn)

        self._start_btn = QPushButton("▶  Start All")
        self._start_btn.setFixedHeight(28)
        self._start_btn.setProperty("class", "primary")
        self._start_btn.clicked.connect(self.start_requested.emit)
        foot_lay.addWidget(self._start_btn)

        root.addWidget(footer)

    def add_job(self, job: Job) -> None:
        self._empty_label.hide()
        row = JobRowWidget(job)
        row.retry_requested.connect(self.retry_requested.emit)
        row.remove_requested.connect(self._on_remove_row)
        row.details_requested.connect(self.show_log.emit)

        self._job_rows[job.id] = row
        # Insert before stretch
        self._list_layout.insertWidget(self._list_layout.count() - 1, row)
        self._update_counts()

    def update_job_status(self, job_id: str, status: JobStatus) -> None:
        if job_id in self._job_rows:
            self._job_rows[job_id].update_status(status)
            self._update_counts()

    def update_job_progress(self, job_id: str, pct: float) -> None:
        if job_id in self._job_rows:
            self._job_rows[job_id].update_progress(pct)

    def remove_job(self, job_id: str) -> None:
        if job_id in self._job_rows:
            row = self._job_rows.pop(job_id)
            self._list_layout.removeWidget(row)
            row.deleteLater()
            self._update_counts()

    def _on_remove_row(self, job_id: str) -> None:
        self.remove_job(job_id)

    def _update_counts(self) -> None:
        count = len(self._job_rows)
        if count == 0:
            self._empty_label.show()
            self._summary_label.setText("0 jobs in queue")
            self._start_btn.setEnabled(False)
            self._cancel_all_btn.hide()
        else:
            self._empty_label.hide()
            self._summary_label.setText(f"{count} job{'s' if count != 1 else ''} in queue")
            self._start_btn.setEnabled(True)

    def _update_overall(self) -> None:
        pass
