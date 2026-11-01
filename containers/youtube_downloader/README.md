# VMT YouTube Downloader Extension

[![License: Unlicense](https://img.shields.io/badge/license-Unlicense-blue.svg)](LICENSE)
[![VMT Extension](https://img.shields.io/badge/VMT-Extension-red.svg)](https://github.com/vmt-project/VMT)
[![Version](https://img.shields.io/badge/version-1.0.1-green.svg)](manifest.json)

First-party extension for **VMT — Versatile Media Toolkit**, providing high-performance, user-friendly YouTube video and audio downloading integrated directly into the VMT desktop application.

---

## Technical Overview

- **Extension ID**: `org.vmt.youtubedownloader`
- **Version**: `1.0.1`
- **Author**: VMT Project
- **Category**: Utility
- **Primary Engine**: `yt-dlp` (vendored in isolated `dependencies/` directory)
- **Post-Processor**: FFmpeg / FFprobe system binaries

---

## Features

- **Instant Metadata Preview**: Paste any valid YouTube URL to fetch video title, high-resolution thumbnail preview, and duration.
- **Quality Presets**: Choose resolution targets (`Best`, `1080p`, `720p`, `480p`, `360p`).
- **Multiple Container Formats**: Video downloads (`MP4`, `MKV`) and audio-only extractions (`MP3`, `M4A`, `WAV`).
- **Real-Time Tracking**: Progress bar with percentage, download speed (KB/s or MB/s), and estimated time remaining (ETA).
- **Non-Blocking Execution**: Asynchronous Qt background threads prevent UI freezing.
- **Download Cancellation**: Instant cancellation without hanging or memory leaks.
- **Output Management**: Custom download directory selection with auto-open output location button.

---

## Repository Structure

```text
VMT-YouTubeDownloader/
│
├── source/
│   ├── __init__.py           # Extension entrypoint subclassing VMTExtension
│   ├── downloader.py         # Asynchronous yt-dlp & FFmpeg thread workers
│   └── ui_page.py            # PySide UI page component (YouTubeDownloaderPage)
│
├── assets/
│   └── icon.png              # High-resolution 256x256 app icon asset
│
├── dependencies/
│   ├── yt_dlp/               # Isolated yt-dlp package files
│   └── yt_dlp-2026.7.4...    # Dependency metadata
│
├── tests/
│   └── test_youtube_downloader.py  # End-to-end automated test suite
│
├── build/
│   └── YouTubeDownloader.vmte # Output packaged extension artifact
│
├── manifest.json             # VMT extension manifest specification
├── build_package.py          # Package builder script (.vmte archive generator)
├── README.md                 # Extension documentation & release guide
├── LICENSE                   # Licensing terms (Unlicense)
└── .gitignore                # Git exclusion rules
```

---

## Building the Package (`.vmte`)

To build the standalone `.vmte` extension package:

```bash
python build_package.py
```

This compiles the source code, manifest, and isolated dependencies into `build/YouTubeDownloader.vmte`.

---

## Testing

Run the 21-assertion automated end-to-end acceptance audit suite:

```bash
python tests/test_youtube_downloader.py
```

---

## Dependency & License Compliance

1. **yt-dlp**:
   - **License**: Unlicense (Public Domain / Free and Unencumbered Software)
   - **Repository**: [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp)
   - **Isolation**: Bundled strictly inside `dependencies/` inside the extension package. It does not modify global Python environment or site-packages.

2. **FFmpeg**:
   - **License**: LGPL v2.1+ / GPL v2+
   - **Integration**: Dynamically invokes external system FFmpeg binary supplied by VMT Core engine context.
