# mediahelper

A command-line tool for converting media files. Currently supports FLAC audio conversion with plans for video support in the future.

## Requirements

- Python 3.10+
- ffmpeg (`sudo apt install ffmpeg`)

## Installation

```bash
pip install -e .
```

## Usage

### Convert FLAC files to 16-bit / 44.1kHz

```bash
mediahelper audio ~/Music/album/ -b 16 -r 44100
```

### Convert specific files to 24-bit / 48kHz

```bash
mediahelper audio track1.flac track2.flac -b 24 -r 48000
```

### Convert to WAV format with custom output directory

```bash
mediahelper audio ~/Music/ -f wav -b 24 -o ~/converted/
```

### Keep original specs, just change format to ALAC

```bash
mediahelper audio ~/Music/album/ -f alac
```

### Preview what would happen (dry run)

```bash
mediahelper audio ~/Music/ -b 16 -r 44100 --dry-run
```

### Parallel conversion with 8 workers

```bash
mediahelper audio ~/Music/ -b 16 -r 44100 -j 8
```

## Options

| Flag | Description |
|------|-------------|
| `-b, --bit-depth` | Target bit depth: 16, 24, or 32 (default: keep original) |
| `-r, --sample-rate` | Target sample rate: 44100, 48000, 88200, 96000, 176400, 192000 (default: keep original) |
| `-f, --format` | Output format: flac, wav, alac (default: flac) |
| `-o, --output-dir` | Output directory (default: `converted/` subfolder next to source) |
| `--overwrite` | Overwrite existing output files |
| `-j, --jobs` | Number of parallel workers (default: CPU core count) |
| `--dry-run` | Show conversion plan without executing |

## Project Structure

```
mediahelper/
├── __init__.py
├── cli.py          # CLI argument parsing and routing
└── audio.py        # Audio conversion logic (ffmpeg)
```

Future video support will be added as `mediahelper/video.py` with a `mediahelper video` subcommand.
