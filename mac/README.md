# Taigi-whisper-Mac

macOS (Apple Silicon) port of [Taigi-whisper-UI](https://github.com/BillyNien/Taigi-whisper-UI).

## Requirements

- macOS with Apple Silicon (M1/M2/M3) or Intel
- Python 3.11
- [uv](https://github.com/astral-sh/uv) (`brew install uv`)
- ffmpeg (`brew install ffmpeg`)

## Quick Start

```bash
cd mac
chmod +x start.sh
./start.sh
```

First run will create a virtual environment and install all packages automatically (may take a few minutes).

## Changes from Windows version

| Item | Windows | Mac |
|------|---------|-----|
| Font | Microsoft JhengHei | PingFang TC |
| Acceleration | CUDA / CPU | MPS / CPU |
| Open folder | `os.startfile` | `open` (Finder) |
| pyannote device | GPU | CPU (MPS stability) |
| Startup script | `start.bat` | `start.sh` |

## Speaker Diarization (pyannote)

Requires a HuggingFace token and acceptance of the following model licenses:
- https://huggingface.co/pyannote/speaker-diarization-3.1
- https://huggingface.co/pyannote/segmentation-3.0
