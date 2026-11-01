"""
job_queue.py
Sequential job queue manager. Processes jobs one at a time using FFmpegRunner threads.
Emits Qt signals so the UI can react to state changes.
"""
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.job import Job, JobStatus
from core.ffmpeg_runner import FFmpegRunner


class JobQueue(QObject):
    """
    Manages a list of Jobs and processes them sequentially.
    """

    # ── Signals ───────────────────────────────────────────────────────────────
    job_added          = Signal(object)            # Job
    job_status_changed = Signal(str, object)       # job_id, JobStatus
    job_progress       = Signal(str, float)        # job_id, pct 0–100
    job_log_line       = Signal(str, str)          # job_id, line
    job_time_info      = Signal(str, float, float, float)  # id, elapsed, eta, pos
    queue_started      = Signal()
    queue_finished     = Signal()                  # all jobs done (or stopped)
    queue_cleared      = Signal()

    def __init__(self, ffmpeg_path: str = "", parent: QObject = None):
        super().__init__(parent)
        self._jobs: list[Job] = []
        self._ffmpeg_path = ffmpeg_path
        self._current_runner: Optional[FFmpegRunner] = None
        self._running = False
        self._stop_remaining = False

    # ── Public API ────────────────────────────────────────────────────────────

    def set_ffmpeg_path(self, path: str) -> None:
        self._ffmpeg_path = path

    @property
    def jobs(self) -> list[Job]:
        return list(self._jobs)

    @property
    def is_running(self) -> bool:
        return self._running

    def add_job(self, job: Job) -> None:
        self._jobs.append(job)
        self.job_added.emit(job)

    def remove_job(self, job_id: str) -> None:
        self._jobs = [j for j in self._jobs if j.id != job_id]

    def clear_completed(self) -> None:
        self._jobs = [j for j in self._jobs
                      if j.status not in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)]
        self.queue_cleared.emit()

    def start(self) -> None:
        """Start processing the queue from the first WAITING job."""
        if self._running:
            return
        self._stop_remaining = False
        self._running = True
        self.queue_started.emit()
        self._process_next()

    def cancel_current(self) -> None:
        """Cancel the currently running job (leave remaining WAITING)."""
        if self._current_runner:
            self._current_runner.stop()

    def cancel_all(self) -> None:
        """Cancel the current job and mark all remaining as Cancelled."""
        self._stop_remaining = True
        self.cancel_current()

    def retry_job(self, job_id: str) -> None:
        """Reset a failed/cancelled job back to WAITING."""
        for job in self._jobs:
            if job.id == job_id:
                job.status = JobStatus.WAITING
                job.progress = 0.0
                job.error_message = ""
                job.ffmpeg_log = ""
                self.job_status_changed.emit(job_id, job.status)
                break

    # ── Internal ─────────────────────────────────────────────────────────────

    def _process_next(self) -> None:
        """Find and start the next WAITING job."""
        next_job = next((j for j in self._jobs if j.status == JobStatus.WAITING), None)

        if next_job is None or self._stop_remaining:
            # Mark remaining as cancelled if stop_remaining
            if self._stop_remaining:
                for j in self._jobs:
                    if j.status == JobStatus.WAITING:
                        j.status = JobStatus.CANCELLED
                        self.job_status_changed.emit(j.id, j.status)
            self._running = False
            self._current_runner = None
            self.queue_finished.emit()
            return

        self._run_job(next_job)

    def _run_job(self, job: Job) -> None:
        runner = FFmpegRunner(job, self._ffmpeg_path)
        self._current_runner = runner

        # Connect signals
        runner.job_started.connect(lambda: self._on_job_started(job))
        runner.progress_updated.connect(lambda pct: self._on_progress(job, pct))
        runner.log_line_received.connect(lambda line: self.job_log_line.emit(job.id, line))
        runner.time_info.connect(
            lambda el, eta, pos: self.job_time_info.emit(job.id, el, eta, pos))
        runner.job_finished.connect(lambda ok, err: self._on_job_finished(job, ok, err))

        runner.start()

    def _on_job_started(self, job: Job) -> None:
        job.status = JobStatus.RUNNING
        self.job_status_changed.emit(job.id, job.status)

    def _on_progress(self, job: Job, pct: float) -> None:
        job.progress = pct
        self.job_progress.emit(job.id, pct)

    def _on_job_finished(self, job: Job, success: bool, error: str) -> None:
        if success:
            job.status = JobStatus.COMPLETED
            job.progress = 100.0
        elif error == "Cancelled":
            job.status = JobStatus.CANCELLED
        else:
            job.status = JobStatus.FAILED
            job.error_message = error

        self.job_status_changed.emit(job.id, job.status)
        self._process_next()

    # ── Stats ─────────────────────────────────────────────────────────────────

    @property
    def total_count(self) -> int:
        return len(self._jobs)

    @property
    def completed_count(self) -> int:
        return sum(1 for j in self._jobs if j.status == JobStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        return sum(1 for j in self._jobs
                   if j.status in (JobStatus.FAILED, JobStatus.CANCELLED))

    @property
    def waiting_count(self) -> int:
        return sum(1 for j in self._jobs if j.status == JobStatus.WAITING)

    @property
    def overall_progress(self) -> float:
        if not self._jobs:
            return 0.0
        total = sum(j.progress for j in self._jobs)
        return total / len(self._jobs)
