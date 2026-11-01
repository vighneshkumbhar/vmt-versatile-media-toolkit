"""
settings.py
Persists user settings to %APPDATA%\\VMT\\config\\settings.json (Windows)
or ~/.local/share/VMT/config/settings.json (Linux/macOS).

Mutable user preferences are NEVER written inside the application
installation directory or _internal/. All runtime state lives under
the platform user-data directory, consistent with extension storage.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from typing import Any


def _get_vmt_data_dir() -> Path:
    r"""
    Returns the VMT user-data root directory.
      Windows : %APPDATA%\VMT
      Linux   : $XDG_DATA_HOME/VMT  (or ~/.local/share/VMT)
      macOS   : ~/Library/Application Support/VMT
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "VMT"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "VMT"
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"
        return base / "VMT"


_VMT_DATA_DIR = _get_vmt_data_dir()
_CONFIG_DIR   = _VMT_DATA_DIR / "config"
_SETTINGS_FILE = _CONFIG_DIR / "settings.json"

# ── Defaults written on first launch ───────────────────────────────────────
# output_folder defaults to "" which resolves to Documents\VMT Output at
# runtime via get_output_folder().  This guarantees no developer path leaks
# into a freshly installed copy.
_DEFAULTS: dict[str, Any] = {
    "output_folder":      "",
    "last_format":        "MP4",
    "last_quality":       "Recommended",
    "overwrite_files":    False,
    "hw_acceleration":    False,
    "hw_encoder":         None,   # 'nvenc' | 'qsv' | 'amf' | None
    "theme":              "dark",
    "window_width":       1240,
    "window_height":      820,
    "window_x":           -1,
    "window_y":           -1,
    "ffmpeg_path":        None,
    "ffprobe_path":       None,
    "show_advanced":      False,
    "log_visible":        False,
    "ext_manager_maximized": False,
    "ext_manager_width":  980,
    "ext_manager_height": 680,
    "ext_manager_x":      -1,
    "ext_manager_y":      -1,
}

_data: dict[str, Any] = {}


def load() -> None:
    """Load settings from the user-data directory, falling back to defaults."""
    global _data
    _data = dict(_DEFAULTS)
    try:
        if _SETTINGS_FILE.exists():
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # Only accept keys we know about to avoid persisting stale cruft
            for key in _DEFAULTS:
                if key in loaded:
                    _data[key] = loaded[key]
    except Exception:
        pass  # silently use defaults on any parse / IO error


def save() -> None:
    """Persist current settings to %APPDATA%\\VMT\\config\\settings.json."""
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(_data, f, indent=2)
    except Exception:
        pass


def get(key: str, default: Any = None) -> Any:
    if not _data:
        load()
    return _data.get(key, _DEFAULTS.get(key, default))


def set(key: str, value: Any) -> None:
    if not _data:
        load()
    _data[key] = value


def get_output_folder() -> str:
    """
    Returns the configured output folder, creating it on demand.
    Falls back to Documents\\VMT Output so new installs have a sane default
    without any developer path baked in.
    """
    folder = get("output_folder", "")
    if not folder:
        folder = str(Path.home() / "Documents" / "VMT Output")
    os.makedirs(folder, exist_ok=True)
    return folder


def get_settings_path() -> Path:
    """Return the absolute path where settings are stored (for diagnostics)."""
    return _SETTINGS_FILE
