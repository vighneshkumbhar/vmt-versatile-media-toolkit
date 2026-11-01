# Product Requirements Document (PRD) — VMT

## 1. Product Overview
- **Product Name**: VMT (Video Media Toolkit)
- **Target Audience**: Content creators, video editors, archivists, developers building media plugins.
- **Core Proposition**: All-in-one desktop video workbench combining intuitive FFmpeg workflows with an open extension ecosystem.

## 2. Functional Requirements Table
| ID | Requirement | Evidence | Status |
|---|---|---|---|
| FR-001 | Asynchronous FFmpeg Runner & Stream Parser | `source/core/ffmpeg_runner.py`, `source/core/ffprobe_info.py` | CONFIRMED |
| FR-002 | Multi-tab Conversion Workflows (Convert, Audio, Compress, GIF, Advanced) | `source/ui/pages/` | CONFIRMED |
| FR-003 | Extension Package Manager (`.vmte`) | `source/extensions/package.py`, `source/extensions/loader.py` | CONFIRMED |
| FR-004 | Extension Manager UI & Store Integration | `source/ui/extension_manager_window.py` | CONFIRMED |
| FR-005 | Job Queue & Background Threading | `source/core/job_queue.py`, `source/core/job.py` | CONFIRMED |
| FR-006 | Drag & Drop Multi-file Ingestion | `source/ui/drop_zone.py`, `source/ui/file_list.py` | CONFIRMED |
| FR-007 | Native Extension SDK & Package Builder | `sdk/vmt_sdk.py`, `sdk/build_vmte.py` | CONFIRMED |
