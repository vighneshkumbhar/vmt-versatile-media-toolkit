"""
time_utils.py
Time formatting utilities.
"""
from __future__ import annotations


def seconds_to_hms(seconds: float) -> str:
    """Convert seconds to HH:MM:SS string."""
    if seconds < 0:
        return "00:00:00"
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"


def hms_to_seconds(hms: str) -> float:
    """Convert HH:MM:SS or MM:SS to seconds. Returns 0 on error."""
    try:
        parts = hms.strip().split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        else:
            return float(parts[0])
    except (ValueError, IndexError):
        return 0.0


def format_eta(seconds: float) -> str:
    """Format ETA string."""
    if seconds <= 0:
        return "—"
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m}m {s}s"
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    return f"{h}h {m}m"


def parse_ffmpeg_time(time_str: str) -> float:
    """
    Parse FFmpeg time string 'HH:MM:SS.ms' to float seconds.
    e.g. '00:01:23.45' → 83.45
    """
    try:
        parts = time_str.strip().split(":")
        if len(parts) == 3:
            h = int(parts[0])
            m = int(parts[1])
            s = float(parts[2])
            return h * 3600 + m * 60 + s
    except (ValueError, IndexError):
        pass
    return 0.0
