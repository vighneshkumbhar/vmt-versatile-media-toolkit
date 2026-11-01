# Codebase Map — VMT

```text
VMT/
├── source/
│   ├── core/                   # FFmpeg runner, job queue, presets
│   │   ├── ffmpeg_finder.py    # Auto-locate FFmpeg in PATH or bin/
│   │   ├── ffmpeg_runner.py    # Subprocess execution & stdout parser
│   │   ├── ffprobe_info.py     # Codec & stream metadata inspector
│   │   └── job_queue.py        # Task scheduling and worker pool
│   ├── extensions/             # VMTE package loader, capabilities, manifest
│   │   ├── api/                # Extension API interfaces (ffmpeg, jobs, media)
│   │   ├── lifecycle.py        # Enable/disable/load hooks
│   │   ├── loader.py           # Import extension module
│   │   └── package.py          # .vmte archive extraction & verification
│   ├── ui/                     # PySide6 desktop views
│   │   ├── drop_zone.py        # File drop target
│   │   ├── extension_manager_window.py # Extension catalog UI
│   │   ├── main_window.py      # App shell, navigation, sidebar
│   │   └── pages/              # Built-in pages (convert, audio, compress, gif)
│   └── main.py                 # Application bootstrap entry point
├── sdk/                        # Official VMT Extension SDK
│   ├── build_vmte.py           # CLI tool to compile .vmte extension packages
│   ├── vmt_sdk.py              # Extension base classes and hooks
│   └── examples/               # Sample extensions (hello, ui, ffmpeg)
├── extensions/                 # Installed local extensions
├── installer/                  # Installer build scripts & UI
├── requirements.txt            # Python dependencies
└── start.bat / build.bat       # Execution and packaging scripts
```
