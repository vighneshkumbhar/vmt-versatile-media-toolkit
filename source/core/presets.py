"""
presets.py
FFmpeg quality/format presets. Translates human labels into FFmpeg args.
"""
from __future__ import annotations
from typing import Optional

# ── Quality presets ──────────────────────────────────────────────────────────

QUALITY_PRESETS: dict[str, dict] = {
    "Best Quality":  {"crf": 18, "preset": "slow",   "audio_br": "320k"},
    "High Quality":  {"crf": 20, "preset": "medium",  "audio_br": "256k"},
    "Recommended":   {"crf": 23, "preset": "medium",  "audio_br": "192k"},
    "Smaller File":  {"crf": 28, "preset": "fast",    "audio_br": "128k"},
    "Smallest File": {"crf": 32, "preset": "faster",  "audio_br": "96k"},
}

# ── Output format groups ─────────────────────────────────────────────────────

VIDEO_FORMATS = ["MP4", "MKV", "MOV", "WebM", "AVI"]
AUDIO_FORMATS = ["MP3", "WAV", "FLAC", "M4A", "OGG", "AAC", "OPUS"]
ALL_OUTPUT_FORMATS = VIDEO_FORMATS + AUDIO_FORMATS + ["GIF"]

# ── Resolution presets ───────────────────────────────────────────────────────

RESOLUTION_PRESETS: dict[str, Optional[tuple[int, int]]] = {
    "Original":   None,
    "4K (2160p)": (3840, 2160),
    "1440p":      (2560, 1440),
    "1080p":      (1920, 1080),
    "720p":       (1280, 720),
    "480p":       (854,  480),
    "360p":       (640,  360),
}

# ── GIF FPS presets ──────────────────────────────────────────────────────────

GIF_FPS_PRESETS = ["5", "10", "15", "24", "30"]


# ── Codec selection ──────────────────────────────────────────────────────────

def get_video_encode_args(output_fmt: str, quality_label: str,
                          hw_encoder: Optional[str] = None) -> list[str]:
    """
    Return FFmpeg args for video+audio encoding given output format and quality.
    hw_encoder: 'nvenc' | 'qsv' | 'amf' | None
    """
    q = QUALITY_PRESETS.get(quality_label, QUALITY_PRESETS["Recommended"])
    crf = q["crf"]
    preset = q["preset"]
    abr = q["audio_br"]
    fmt = output_fmt.lower()

    if fmt in ("mp4", "mkv", "mov"):
        if hw_encoder == "nvenc":
            return ["-c:v", "h264_nvenc", "-rc", "vbr", "-cq", str(crf),
                    "-preset", "p4", "-c:a", "aac", "-b:a", abr]
        elif hw_encoder == "qsv":
            return ["-c:v", "h264_qsv", "-global_quality", str(crf),
                    "-c:a", "aac", "-b:a", abr]
        elif hw_encoder == "amf":
            return ["-c:v", "h264_amf", "-rc", "1", "-qp_i", str(crf),
                    "-c:a", "aac", "-b:a", abr]
        else:
            return ["-c:v", "libx264", "-crf", str(crf),
                    "-preset", preset, "-c:a", "aac", "-b:a", abr]

    elif fmt == "webm":
        return ["-c:v", "libvpx-vp9", "-crf", str(crf), "-b:v", "0",
                "-c:a", "libopus", "-b:a", abr]

    elif fmt == "avi":
        return ["-c:v", "mpeg4", "-qscale:v", "5",
                "-c:a", "libmp3lame", "-b:a", abr]

    else:
        return ["-c:v", "libx264", "-crf", str(crf),
                "-preset", preset, "-c:a", "aac", "-b:a", abr]


def get_audio_encode_args(output_fmt: str, quality_label: str) -> list[str]:
    """Return FFmpeg args for audio-only output."""
    q = QUALITY_PRESETS.get(quality_label, QUALITY_PRESETS["Recommended"])
    abr = q["audio_br"]
    fmt = output_fmt.lower()

    if fmt == "mp3":
        return ["-vn", "-c:a", "libmp3lame", "-b:a", abr]
    elif fmt == "wav":
        return ["-vn", "-c:a", "pcm_s16le"]
    elif fmt == "flac":
        return ["-vn", "-c:a", "flac"]
    elif fmt == "m4a":
        return ["-vn", "-c:a", "aac", "-b:a", abr]
    elif fmt == "ogg":
        return ["-vn", "-c:a", "libvorbis", "-b:a", abr]
    elif fmt == "aac":
        return ["-vn", "-c:a", "aac", "-b:a", abr]
    elif fmt == "opus":
        return ["-vn", "-c:a", "libopus", "-b:a", abr]
    else:
        return ["-vn", "-c:a", "aac", "-b:a", abr]


def get_resize_filter(width: int, height: int, keep_aspect: bool = True) -> list[str]:
    """Return FFmpeg video filter args for resizing."""
    if keep_aspect:
        # Use -2 to maintain aspect ratio and ensure divisibility by 2
        return ["-vf", f"scale={width}:-2"]
    else:
        return ["-vf", f"scale={width}:{height}"]


def get_gif_args(fps: int, width: int, start: str, duration: str) -> list[str]:
    """Return FFmpeg args for GIF output with palette optimization."""
    filters = []
    if width and width > 0:
        filters.append(f"scale={width}:-1:flags=lanczos")
    filters.append(f"fps={fps}")
    filter_str = ",".join(filters)

    args = []
    if start:
        args += ["-ss", start]
    if duration:
        args += ["-t", duration]

    # Two-pass GIF: palette generation + dithering for quality
    # Simplified single-pass for practical use:
    args += [
        "-vf", f"{filter_str},split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse=dither=bayer",
        "-loop", "0"
    ]
    return args


def format_to_extension(fmt: str) -> str:
    """Convert display format name to file extension."""
    return fmt.lower()


def extension_to_format(ext: str) -> str:
    """Convert file extension to display format name."""
    mapping = {
        "mp4": "MP4", "mkv": "MKV", "mov": "MOV",
        "webm": "WebM", "avi": "AVI",
        "mp3": "MP3", "wav": "WAV", "flac": "FLAC",
        "m4a": "M4A", "ogg": "OGG", "aac": "AAC", "opus": "OPUS",
        "gif": "GIF",
    }
    return mapping.get(ext.lower(), ext.upper())
