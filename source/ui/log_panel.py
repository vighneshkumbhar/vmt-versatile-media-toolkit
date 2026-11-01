"""
log_panel.py
Collapsible panel showing FFmpeg command and output log.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QFileDialog, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QTextCursor

from ui.styles import COLORS as C


class LogPanel(QWidget):
    """
    Collapsible log viewer.
    Shows the FFmpeg command and stderr output for any job.
    """

    visibility_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_job_id: str = ""
        self._current_command: str = ""
        self._log_data: dict[str, str] = {}      # job_id → full log
        self._command_data: dict[str, str] = {}  # job_id → command
        self._visible = False
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet(f"""
            background: {C['bg_dark']};
            border-top: 1px solid {C['border']};
        """)
        header.setFixedHeight(40)
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(16, 0, 16, 0)
        hlay.setSpacing(10)

        log_icon = QLabel("📋")
        log_icon.setStyleSheet("background: transparent; font-size: 14px;")

        self._header_label = QLabel("Details / Log")
        self._header_label.setStyleSheet(f"""
            color: {C['text_muted']};
            font-size: 13px;
            font-weight: 600;
            background: transparent;
        """)

        self._toggle_btn = QPushButton("▲  Show")
        self._toggle_btn.setProperty("class", "ghost")
        self._toggle_btn.setFixedHeight(24)
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {C['border']};
                border-radius: 5px;
                color: {C['text_muted']};
                font-size: 11px;
                padding: 0 10px;
            }}
            QPushButton:hover {{ background: {C['bg_card']}; color: white; }}
        """)
        self._toggle_btn.clicked.connect(self.toggle_visibility)

        hlay.addWidget(log_icon)
        hlay.addWidget(self._header_label)
        hlay.addStretch()
        hlay.addWidget(self._toggle_btn)

        # ── Content (collapsible) ────────────────────────────────────
        self._content = QWidget()
        self._content.setStyleSheet(f"background: {C['bg_dark']};")
        self._content.hide()

        clayout = QVBoxLayout(self._content)
        clayout.setContentsMargins(12, 8, 12, 12)
        clayout.setSpacing(8)

        # Command bar
        cmd_row = QHBoxLayout()
        cmd_label = QLabel("Command:")
        cmd_label.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; font-weight: 600; background: transparent;")
        self._copy_cmd_btn = QPushButton("Copy command")
        self._copy_cmd_btn.setFixedHeight(24)
        self._copy_cmd_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {C['border']};
                color: {C['text_muted']};
                font-size: 11px;
                border-radius: 5px;
                padding: 0 8px;
            }}
            QPushButton:hover {{ background: {C['bg_card']}; color: white; }}
        """)
        self._copy_cmd_btn.clicked.connect(self._copy_command)

        self._copy_log_btn = QPushButton("Copy log")
        self._copy_log_btn.setFixedHeight(24)
        self._copy_log_btn.setStyleSheet(self._copy_cmd_btn.styleSheet())
        self._copy_log_btn.clicked.connect(self._copy_log)

        self._save_log_btn = QPushButton("Save log")
        self._save_log_btn.setFixedHeight(24)
        self._save_log_btn.setStyleSheet(self._copy_cmd_btn.styleSheet())
        self._save_log_btn.clicked.connect(self._save_log)

        cmd_row.addWidget(cmd_label)
        cmd_row.addStretch()
        cmd_row.addWidget(self._copy_cmd_btn)
        cmd_row.addWidget(self._copy_log_btn)
        cmd_row.addWidget(self._save_log_btn)

        self._cmd_display = QPlainTextEdit()
        self._cmd_display.setReadOnly(True)
        self._cmd_display.setMaximumHeight(48)
        self._cmd_display.setPlaceholderText("No command yet")
        self._cmd_display.setStyleSheet(f"""
            background: {C['bg_dark']};
            border: 1px solid {C['border']};
            border-radius: 6px;
            color: {C['accent_light']};
            font-family: Consolas, monospace;
            font-size: 11px;
            padding: 4px 8px;
        """)

        log_label = QLabel("FFmpeg output:")
        log_label.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; font-weight: 600; background: transparent;")

        self._log_display = QPlainTextEdit()
        self._log_display.setReadOnly(True)
        self._log_display.setMinimumHeight(120)
        self._log_display.setMaximumHeight(200)
        self._log_display.setPlaceholderText("No output yet")
        self._log_display.setStyleSheet(f"""
            background: {C['bg_dark']};
            border: 1px solid {C['border']};
            border-radius: 6px;
            color: {C['text_muted']};
            font-family: Consolas, monospace;
            font-size: 11px;
            padding: 4px 8px;
        """)

        clayout.addLayout(cmd_row)
        clayout.addWidget(self._cmd_display)
        clayout.addWidget(log_label)
        clayout.addWidget(self._log_display)

        root.addWidget(header)
        root.addWidget(self._content)

    # ── Public API ──────────────────────────────────────────────────────────

    def toggle_visibility(self) -> None:
        self._visible = not self._visible
        if self._visible:
            self._content.show()
            self._toggle_btn.setText("▼  Hide")
        else:
            self._content.hide()
            self._toggle_btn.setText("▲  Show")
        self.visibility_toggled.emit(self._visible)

    def show_job_log(self, job_id: str) -> None:
        """Switch to displaying a specific job's log."""
        self._current_job_id = job_id
        cmd = self._command_data.get(job_id, "")
        log = self._log_data.get(job_id, "")
        self._cmd_display.setPlainText(cmd)
        self._log_display.setPlainText(log)
        if not self._visible:
            self.toggle_visibility()

    def append_log_line(self, job_id: str, line: str) -> None:
        """Append a live log line for a running job."""
        self._log_data[job_id] = self._log_data.get(job_id, "") + line + "\n"
        if job_id == self._current_job_id and self._visible:
            self._log_display.appendPlainText(line)
            # Auto-scroll
            cursor = self._log_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            self._log_display.setTextCursor(cursor)

    def set_job_command(self, job_id: str, command: str) -> None:
        self._command_data[job_id] = command
        if job_id == self._current_job_id and self._visible:
            self._cmd_display.setPlainText(command)

    def clear_for_job(self, job_id: str) -> None:
        """Prepare log panel for a new job (clear display, set as current)."""
        self._current_job_id = job_id
        self._log_data[job_id] = ""
        self._command_data[job_id] = ""
        if self._visible:
            self._cmd_display.clear()
            self._log_display.clear()

    # ── Clipboard / File ────────────────────────────────────────────────────

    def _copy_command(self) -> None:
        from PySide6.QtWidgets import QApplication
        cmd = self._command_data.get(self._current_job_id, "")
        if cmd:
            QApplication.clipboard().setText(cmd)
            self._copy_cmd_btn.setText("Copied!")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self._copy_cmd_btn.setText("Copy command"))

    def _copy_log(self) -> None:
        from PySide6.QtWidgets import QApplication
        log = self._log_data.get(self._current_job_id, "")
        if log:
            QApplication.clipboard().setText(log)
            self._copy_log_btn.setText("Copied!")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self._copy_log_btn.setText("Copy log"))

    def _save_log(self) -> None:
        log = self._log_data.get(self._current_job_id, "")
        if not log:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Log", "ffmpeg_log.txt", "Text Files (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    cmd = self._command_data.get(self._current_job_id, "")
                    if cmd:
                        f.write(f"Command:\n{cmd}\n\n")
                    f.write("Output:\n" + log)
            except Exception as e:
                pass  # Fail silently
