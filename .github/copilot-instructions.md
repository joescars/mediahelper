# Copilot Instructions for mediahelper

## Overview

mediahelper is a CLI tool for converting media files, built with Python 3.10+ and ffmpeg. It currently supports audio conversion (FLAC → FLAC/WAV/ALAC) with plans for a future `video` subcommand.

## Setup

```bash
pip install -e .
```

Requires ffmpeg on the system (`sudo apt install ffmpeg`).

## Architecture

- **`cli.py`** — Argument parsing with `argparse`. Subcommand routing lives in `main()`. Each media type (audio, future video) is a subcommand with its own parser.
- **`audio.py`** — Core conversion logic. Builds ffmpeg commands, runs them via `subprocess`, and parallelizes with `ProcessPoolExecutor`. The `ConversionJob` dataclass is the unit of work passed to worker processes.
- **`picker.py`** — Interactive terminal file/folder picker using raw terminal input (no external TUI library). Handles both Unix (`termios`) and Windows (`msvcrt`) key reading.

New media types should follow the same pattern: add a `<type>.py` module with a `convert_<type>(args)` entrypoint, then wire it up as a subcommand in `cli.py`.

## Conventions

- No external runtime dependencies — only stdlib and ffmpeg as a system tool.
- Audio resampling uses the SoX Resampler (`-af aresample=resampler=soxr`) for all sample rate conversions.
- Bit depth and sample rate mappings are centralized in `BIT_DEPTH_CODEC_MAP` and the `SUPPORTED_*` constants at the top of `audio.py`. Update these when adding codec support.
- Output defaults to a `converted/` subfolder next to the source file when no `-o` is given.
- The `ConversionJob` dataclass must remain picklable since it's sent across process boundaries via `ProcessPoolExecutor`.
