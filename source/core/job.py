"""
job.py
Job dataclass representing a single media processing task.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class JobStatus(Enum):
    WAITING = "Waiting"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


@dataclass
class Job:
    """Represents one FFmpeg processing task."""

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Files
    input_file: str = ""
    output_file: str = ""

    # Operation metadata
    operation: str = ""          # e.g. "Convert", "Compress", "Extract Audio"
    description: str = ""        # Human-readable description shown in queue

    # FFmpeg
    ffmpeg_args: List[str] = field(default_factory=list)
    ffmpeg_command: str = ""     # Formatted full command string (for display)
    ffmpeg_log: str = ""         # All stderr output collected

    # State
    status: JobStatus = JobStatus.WAITING
    progress: float = 0.0        # 0–100
    error_message: str = ""

    # Timing (seconds)
    duration: float = 0.0        # total input duration, for progress calculation
    elapsed: float = 0.0

    @property
    def input_name(self) -> str:
        """Basename of input file."""
        import os
        return os.path.basename(self.input_file)

    @property
    def output_name(self) -> str:
        """Basename of output file."""
        import os
        return os.path.basename(self.output_file)
