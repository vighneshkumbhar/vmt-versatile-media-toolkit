# Project Overview — VMT (Video Media Toolkit)

## Executive Summary
**VMT (Video Media Toolkit)** is an open, modular, desktop media processing workstation designed for video conversion, audio extraction, lossless compression, GIF creation, batch transcoding, and ecosystem plugin management.

## Core Value Proposition
- **High-Performance FFmpeg Integration**: Automated FFmpeg binary discovery, asynchronous worker thread runner, real-time stdout progress parsing, and job queue management.
- **Extensibility SDK & Package Manager**: First-class plugin system supporting `.vmte` extension packages with sandboxed capabilities, lifecycle hooks, manifest validation, and dynamic UI page injection.
- **Modern Desktop UI**: Built with PySide6 / Qt providing drag-and-drop media ingestion, real-time encoding preview, hardware acceleration toggles, and detailed job logs.
- **Secure Ecosystem Storage**: SQLite-backed registry (`vmt_ecosystem.db`) for tracking extension versions, capabilities, job history, and user presets.
