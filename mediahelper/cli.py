"""Main CLI entry point for mediahelper."""

import argparse
import sys

from mediahelper.audio import (
    convert_audio,
    SUPPORTED_BIT_DEPTHS,
    SUPPORTED_INPUT_EXTENSIONS,
    SUPPORTED_SAMPLE_RATES,
)
from mediahelper.picker import interactive_select_paths, interactive_select_option


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mediahelper",
        description="Convert media files. Currently supports FLAC audio conversion.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Audio conversion subcommand
    audio_parser = subparsers.add_parser("audio", help="Convert audio files")
    audio_parser.add_argument(
        "inputs",
        nargs="*",
        help="Files or directories to convert (directories are scanned recursively for .flac files)",
    )
    audio_parser.add_argument(
        "--picker",
        action="store_true",
        help="Open an interactive file/folder picker (arrow keys + spacebar) before conversion",
    )
    audio_parser.add_argument(
        "-b", "--bit-depth",
        type=int,
        choices=SUPPORTED_BIT_DEPTHS,
        default=None,
        help="Target bit depth (default: keep original)",
    )
    audio_parser.add_argument(
        "-r", "--sample-rate",
        type=int,
        choices=SUPPORTED_SAMPLE_RATES,
        default=None,
        help="Target sample rate in Hz (default: keep original)",
    )
    audio_parser.add_argument(
        "-f", "--format",
        choices=["flac", "wav", "alac"],
        default="flac",
        help="Output format (default: flac)",
    )
    audio_parser.add_argument(
        "-o", "--output-dir",
        default=None,
        help="Output directory (default: same directory as source, with 'converted' subfolder)",
    )
    audio_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files",
    )
    audio_parser.add_argument(
        "-j", "--jobs",
        type=int,
        default=None,
        help="Number of parallel conversions (default: number of CPU cores)",
    )
    audio_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually converting",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.command is None:
        parse_args(["--help"])
        return 1

    if args.command == "audio":
        if args.picker or not args.inputs:
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                print(
                    "Interactive picker requires a TTY. Provide input paths as arguments instead.",
                    file=sys.stderr,
                )
                return 1
            picked = interactive_select_paths(file_extensions=SUPPORTED_INPUT_EXTENSIONS)
            if not picked:
                print("No inputs selected. Exiting.", file=sys.stderr)
                return 1
            args.inputs = picked

            # Prompt for conversion settings
            fmt = interactive_select_option(
                "Select output format:",
                [("flac", "FLAC"), ("wav", "WAV"), ("alac", "ALAC")],
            )
            if fmt is None:
                print("Cancelled.", file=sys.stderr)
                return 1
            args.format = fmt

            bd = interactive_select_option(
                "Select bit depth:",
                [("keep", "Keep original")]
                + [(str(b), f"{b}-bit") for b in SUPPORTED_BIT_DEPTHS],
            )
            if bd is None:
                print("Cancelled.", file=sys.stderr)
                return 1
            args.bit_depth = None if bd == "keep" else int(bd)

            sr = interactive_select_option(
                "Select sample rate:",
                [("keep", "Keep original")]
                + [(str(r), f"{r // 1000}.{(r % 1000) // 100}kHz" if r % 1000 else f"{r // 1000}kHz") for r in SUPPORTED_SAMPLE_RATES],
            )
            if sr is None:
                print("Cancelled.", file=sys.stderr)
                return 1
            args.sample_rate = None if sr == "keep" else int(sr)
        return convert_audio(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
