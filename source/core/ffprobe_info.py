"""
ffprobe_info.py
Uses ffprobe to extract media metadata and returns it in a clean structure.
"""
from __future__ import annotations
import json
import subprocess
from dataclasses import dataclass, field
from typing import Optional
from utils.file_utils import human_size


@dataclass
class StreamInfo:
    codec_type: str = ""       # "video" or "audio"
    codec_name: str = ""
    codec_long_name: str = ""
    width: int = 0
    height: int = 0
    fps: float = 0.0
    bitrate_kbps: float = 0.0
    sample_rate: int = 0
    channels: int = 0
    channel_layout: str = ""
    pixel_fmt: str = ""


@dataclass
class MediaInfo:
    path: str = ""
    duration: float = 0.0         # seconds
    file_size: int = 0            # bytes
    overall_bitrate_kbps: float = 0.0
    video_streams: list[StreamInfo] = field(default_factory=list)
    audio_streams: list[StreamInfo] = field(default_factory=list)
    error: str = ""

    @property
    def has_video(self) -> bool:
        return len(self.video_streams) > 0

    @property
    def has_audio(self) -> bool:
        return len(self.audio_streams) > 0

    @property
    def primary_video(self) -> Optional[StreamInfo]:
        return self.video_streams[0] if self.video_streams else None

    @property
    def primary_audio(self) -> Optional[StreamInfo]:
        return self.audio_streams[0] if self.audio_streams else None

    @property
    def duration_hms(self) -> str:
        from utils.time_utils import seconds_to_hms
        return seconds_to_hms(self.duration)

    @property
    def file_size_human(self) -> str:
        return human_size(self.file_size)

    def friendly_summary(self) -> dict[str, str]:
        """Return a dict of human-readable label → value pairs for the info panel."""
        items = {}
        v = self.primary_video
        a = self.primary_audio

        if v:
            items["Resolution"] = f"{v.width} × {v.height}" if v.width else "—"
            items["Video Codec"] = v.codec_name.upper() if v.codec_name else "—"
            items["Frame Rate"] = f"{v.fps:.2f} FPS" if v.fps else "—"
            if v.bitrate_kbps:
                br = v.bitrate_kbps
                items["Video Bitrate"] = f"{br/1000:.1f} Mbps" if br >= 1000 else f"{br:.0f} kbps"

        if a:
            items["Audio Codec"] = a.codec_name.upper() if a.codec_name else "—"
            if a.sample_rate:
                items["Sample Rate"] = f"{a.sample_rate/1000:.1f} kHz"
            if a.channel_layout:
                items["Channels"] = a.channel_layout.capitalize()
            elif a.channels:
                items["Channels"] = "Mono" if a.channels == 1 else "Stereo" if a.channels == 2 else str(a.channels)

        items["Duration"] = self.duration_hms
        items["File Size"] = self.file_size_human

        return items


def probe(ffprobe_path: str, file_path: str) -> MediaInfo:
    """
    Run ffprobe on a file and return a MediaInfo object.
    Never raises — errors are captured in MediaInfo.error.
    """
    info = MediaInfo(path=file_path)

    try:
        info.file_size = _get_file_size(file_path)
    except Exception:
        pass

    if not ffprobe_path:
        info.error = "ffprobe not found"
        return info

    try:
        cmd = [
            ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )

        if result.returncode != 0:
            info.error = result.stderr.strip() or "ffprobe returned error"
            return info

        data = json.loads(result.stdout)

        # Parse format section
        fmt = data.get("format", {})
        info.duration = float(fmt.get("duration", 0))
        total_br = fmt.get("bit_rate")
        if total_br:
            info.overall_bitrate_kbps = float(total_br) / 1000

        # Parse streams
        for stream in data.get("streams", []):
            codec_type = stream.get("codec_type", "")
            s = StreamInfo(
                codec_type=codec_type,
                codec_name=stream.get("codec_name", ""),
                codec_long_name=stream.get("codec_long_name", ""),
            )

            if codec_type == "video":
                s.width = stream.get("width", 0)
                s.height = stream.get("height", 0)
                # Parse FPS from avg_frame_rate
                fps_str = stream.get("avg_frame_rate", "0/1")
                s.fps = _parse_fraction(fps_str)
                br = stream.get("bit_rate")
                if br:
                    s.bitrate_kbps = float(br) / 1000
                s.pixel_fmt = stream.get("pix_fmt", "")
                info.video_streams.append(s)

            elif codec_type == "audio":
                s.sample_rate = int(stream.get("sample_rate", 0))
                s.channels = stream.get("channels", 0)
                s.channel_layout = stream.get("channel_layout", "")
                br = stream.get("bit_rate")
                if br:
                    s.bitrate_kbps = float(br) / 1000
                info.audio_streams.append(s)

    except subprocess.TimeoutExpired:
        info.error = "ffprobe timed out"
    except json.JSONDecodeError as e:
        info.error = f"Failed to parse ffprobe output: {e}"
    except Exception as e:
        info.error = str(e)

    return info


def _get_file_size(path: str) -> int:
    import os
    return os.path.getsize(path)


def _parse_fraction(s: str) -> float:
    """Parse '30000/1001' → float."""
    try:
        parts = s.split("/")
        if len(parts) == 2 and int(parts[1]) != 0:
            return float(parts[0]) / float(parts[1])
        return float(parts[0])
    except Exception:
        return 0.0
