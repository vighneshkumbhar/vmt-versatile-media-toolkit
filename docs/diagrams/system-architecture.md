# Architecture Diagram

```mermaid
flowchart TD
  PySideUI --> JobQueue --> FFmpegRunner --> FFmpegProcess
  PySideUI --> ExtensionLoader --> VMTPlugins
```
