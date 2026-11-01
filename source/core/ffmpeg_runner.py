"""
ffmpeg_runner.py
QThread-based FFmpeg process runner with real-time progress parsing.
"""
from __future__ import annotations
import re
import subprocess
import time
from typing import Optional

from PySide6.QtCore import QThread, Signal

from core.job import Job, JobStatus
from utils.time_utils import parse_ffmpeg_time

# CREATE_NO_WINDOW flag for Windows — prevents console window from appearing
_NO_WINDOW = 0x08000000


class FFmpegRunner(QThread):
    """
    Runs a single FFmpeg job in a background thread.
    Emits signals for the UI to react to.
    """

    # Signals
    progress_updated = Signal(float)          # 0–100
    log_line_received = Signal(str)           # one line of stderr
    job_started = Signal()
    job_finished = Signal(bool, str)          # success: bool, error_message: str
    time_info = Signal(float, float, float)   # elapsed, eta, current_time_pos

    def __init__(self, job: Job, ffmpeg_path: str, parent=None):
        super().__init__(parent)
        self._job = job
        self._ffmpeg_path = ffmpeg_path
        self._process: Optional[subprocess.Popen] = None
        self._stopped = False
        self._start_time = 0.0

    @property
    def job(self) -> Job:
        return self._job

    def stop(self) -> None:
        """Request cancellation of the running FFmpeg process."""
        self._stopped = True
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                # Give it a moment, then force-kill
                for _ in range(10):
                    if self._process.poll() is not None:
                        break
                    time.sleep(0.1)
                if self._process.poll() is None:
                    self._process.kill()
            except Exception:
                pass

    def run(self) -> None:
        """Thread entry point — runs FFmpeg and parses output."""
        self._stopped = False
        self._start_time = time.time()

        cmd = [self._ffmpeg_path, "-y"] + self._job.ffmpeg_args
        # Store the readable command in the job
        self._job.ffmpeg_command = " ".join(f'"{a}"' if " " in a else a for a in cmd)
        self._job.ffmpeg_log = ""

        self.job_started.emit()

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=_NO_WINDOW,
            )

            for line in iter(self._process.stdout.readline, ""):
                if self._stopped:
                    break
                line = line.rstrip()
                self._job.ffmpeg_log += line + "\n"
                self.log_line_received.emit(line)
                self._parse_progress_line(line)

            self._process.stdout.close()
            self._process.wait()

            if self._stopped:
                self.job_finished.emit(False, "Cancelled")
                return

            rc = self._process.returncode
            if rc == 0:
                self.progress_updated.emit(100.0)
                self.job_finished.emit(True, "")
            else:
                # Extract last meaningful error line
                err = self._extract_error(self._job.ffmpeg_log)
                self.job_finished.emit(False, err)

        except FileNotFoundError:
            self.job_finished.emit(False, f"FFmpeg not found at: {self._ffmpeg_path}")
        except Exception as e:
            self.job_finished.emit(False, str(e))

    def _parse_progress_line(self, line: str) -> None:
        """
        Parse FFmpeg stderr progress line.
        Example: frame=  120 fps= 30 q=23.0 size=    1024kB time=00:00:04.00 bitrate= 2048.0kbits/s speed=   2x
        """
        if "time=" not in line or self._job.duration <= 0:
            return

        m = re.search(r"time=(\d{2}:\d{2}:\d{2}\.\d+)", line)
        if not m:
            return

        current = parse_ffmpeg_time(m.group(1))
        if current <= 0:
            return

        pct = min(100.0, (current / self._job.duration) * 100.0)
        self.progress_updated.emit(pct)

        elapsed = time.time() - self._start_time
        if pct > 0:
            eta = elapsed * (100.0 - pct) / pct
        else:
            eta = 0.0

        self.time_info.emit(elapsed, eta, current)

    @staticmethod
    def _extract_error(log: str) -> str:
        """Pull the most useful error line from FFmpeg output."""
        lines = log.strip().splitlines()
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith("frame=") and not line.startswith("size="):
                if any(kw in line.lower() for kw in
                       ("error", "invalid", "no such", "failed", "unable", "codec", "muxer")):
                    return line
        # Fall back to last non-empty line
        for line in reversed(lines):
            if line.strip():
                return line.strip()
        return "FFmpeg exited with an error"
