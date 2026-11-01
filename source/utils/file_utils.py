"""
file_utils.py
Utilities for safe output file naming and path handling.
"""
from __future__ import annotations
import os
from pathlib import Path


def safe_output_path(input_path: str, output_dir: str, extension: str,
                     suffix: str = "_converted", overwrite: bool = False) -> str:
    """
    Generate a safe output file path that won't silently overwrite existing files.

    If overwrite=True, returns the plain path (may overwrite).
    If overwrite=False, appends _1, _2, ... until a free path is found.

    Args:
        input_path: Original input file path (used to derive name)
        output_dir: Destination directory
        extension: Output extension without dot, e.g. 'mp4'
        suffix: Suffix appended to stem, e.g. '_converted'
        overwrite: If True, allow overwriting

    Returns:
        Absolute path string for the output file.
    """
    stem = Path(input_path).stem
    ext = extension.lstrip(".")
    base = f"{stem}{suffix}.{ext}"

    os.makedirs(output_dir, exist_ok=True)

    candidate = os.path.join(output_dir, base)
    if overwrite or not os.path.exists(candidate):
        return candidate

    # Find next free numbered slot
    counter = 1
    while True:
        candidate = os.path.join(output_dir, f"{stem}{suffix}_{counter}.{ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def human_size(bytes_: int) -> str:
    """Convert bytes to human-readable string."""
    if bytes_ < 1024:
        return f"{bytes_} B"
    kb = bytes_ / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"
    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.1f} MB"
    gb = mb / 1024
    return f"{gb:.2f} GB"


def is_supported_media(path: str) -> bool:
    """Quick extension check — FFmpeg can handle much more, but this covers common formats."""
    ext = Path(path).suffix.lower().lstrip(".")
    return ext in {
        "mp4", "mkv", "mov", "avi", "webm", "flv", "wmv", "mpeg", "mpg",
        "m4v", "ts", "m2ts", "3gp", "3g2", "ogv", "vob", "divx", "f4v",
        "mp3", "wav", "flac", "aac", "m4a", "ogg", "opus", "wma", "aiff",
        "aif", "mka", "mpa", "ra", "rm", "amr", "ac3", "dts",
        "gif", "webp",
    }
