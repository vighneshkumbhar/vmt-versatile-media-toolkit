# Business Logic — VMT

- **FFmpeg Progress Parsing**: Regular expression extraction matching `time=(\d+):(\d+):(\d+\.\d+)` and `bitrate=\s*(\d+)kbits/s` to compute percentage relative to total duration.
- **Extension Sandboxing**: Extensions only acquire capabilities explicitly declared in `manifest.json`.
