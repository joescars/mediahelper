"""Audio conversion module using ffmpeg."""

import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_BIT_DEPTHS = [16, 24, 32]
SUPPORTED_SAMPLE_RATES = [44100, 48000, 88200, 96000, 176400, 192000]
SUPPORTED_INPUT_EXTENSIONS = {".flac"}

# Maps bit depth to ffmpeg sample_fmt values per output format
BIT_DEPTH_CODEC_MAP = {
    "flac": {16: "s16", 24: "s32", 32: "s32"},
    "wav": {16: "s16", 24: "s24", 32: "s32"},
    "alac": {16: "s16p", 24: "s32p", 32: "s32p"},
}

FORMAT_EXTENSION = {
    "flac": ".flac",
    "wav": ".wav",
    "alac": ".m4a",
}


@dataclass
class ConversionJob:
    """Represents a single file conversion task."""
    input_path: Path
    output_path: Path
    bit_depth: int | None
    sample_rate: int | None
    output_format: str


def find_audio_files(inputs: list[str]) -> list[Path]:
    """Recursively find all supported audio files from given paths."""
    files: list[Path] = []
    seen: set[Path] = set()
    for input_path in inputs:
        p = Path(input_path).resolve()
        if p.is_file() and p.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS and p not in seen:
            files.append(p)
            seen.add(p)
        elif p.is_dir():
            for ext in SUPPORTED_INPUT_EXTENSIONS:
                for match in sorted(p.rglob(f"*{ext}")):
                    resolved = match.resolve()
                    if resolved not in seen:
                        files.append(resolved)
                        seen.add(resolved)
        else:
            print(f"Warning: skipping '{input_path}' (not a file or directory)", file=sys.stderr)
    return files


def build_output_path(input_path: Path, output_dir: Path | None, output_format: str) -> Path:
    """Determine the output file path for a given input."""
    ext = FORMAT_EXTENSION[output_format]
    new_name = input_path.stem + ext

    if output_dir:
        # Preserve relative directory structure under output_dir
        return output_dir / new_name
    else:
        # Place converted file in a 'converted' subfolder next to the source
        converted_dir = input_path.parent / "converted"
        return converted_dir / new_name


def build_ffmpeg_command(job: ConversionJob) -> list[str]:
    """Build the ffmpeg command for a conversion job."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "warning", "-y", "-i", str(job.input_path)]

    if job.output_format == "flac":
        cmd.extend(["-c:a", "flac"])
        if job.bit_depth:
            sample_fmt = BIT_DEPTH_CODEC_MAP["flac"][job.bit_depth]
            cmd.extend(["-sample_fmt", sample_fmt])
    elif job.output_format == "wav":
        if job.bit_depth:
            sample_fmt = BIT_DEPTH_CODEC_MAP["wav"][job.bit_depth]
            cmd.extend(["-c:a", f"pcm_{sample_fmt}le"])
        else:
            cmd.extend(["-c:a", "pcm_s24le"])
    elif job.output_format == "alac":
        cmd.extend(["-c:a", "alac"])
        if job.bit_depth:
            sample_fmt = BIT_DEPTH_CODEC_MAP["alac"][job.bit_depth]
            cmd.extend(["-sample_fmt", sample_fmt])

    if job.sample_rate:
        cmd.extend(["-af", "aresample=resampler=soxr", "-ar", str(job.sample_rate)])

    cmd.append(str(job.output_path))
    return cmd


def run_conversion(job: ConversionJob) -> tuple[Path, bool, str]:
    """Execute a single conversion job. Returns (path, success, message)."""
    try:
        job.output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = build_ffmpeg_command(job)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            return (job.input_path, False, result.stderr.strip())
        return (job.input_path, True, "")
    except subprocess.TimeoutExpired:
        return (job.input_path, False, "Conversion timed out (>10 min)")
    except Exception as e:
        return (job.input_path, False, str(e))


def check_ffmpeg() -> bool:
    """Verify ffmpeg is available on the system."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_audio(args) -> int:
    """Main audio conversion entrypoint."""
    if not check_ffmpeg():
        print("Error: ffmpeg not found. Install it with: sudo apt install ffmpeg", file=sys.stderr)
        return 1

    files = find_audio_files(args.inputs)
    if not files:
        print("No supported audio files found in the specified inputs.", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else None

    # Build conversion jobs
    jobs: list[ConversionJob] = []
    for f in files:
        out_path = build_output_path(f, output_dir, args.format)
        if out_path.exists() and not args.overwrite:
            print(f"  Skipping (exists): {out_path}")
            continue
        jobs.append(ConversionJob(
            input_path=f,
            output_path=out_path,
            bit_depth=args.bit_depth,
            sample_rate=args.sample_rate,
            output_format=args.format,
        ))

    if not jobs:
        print("Nothing to convert (all outputs already exist).")
        return 0

    # Print summary
    spec_parts = []
    if args.bit_depth:
        spec_parts.append(f"{args.bit_depth}-bit")
    if args.sample_rate:
        spec_parts.append(f"{args.sample_rate} Hz")
    spec_parts.append(args.format.upper())
    spec_str = " / ".join(spec_parts)

    print(f"\nConversion plan:")
    print(f"  Files:  {len(jobs)}")
    print(f"  Target: {spec_str}")
    if output_dir:
        print(f"  Output: {output_dir}")
    print()

    if args.dry_run:
        for job in jobs:
            print(f"  [dry-run] {job.input_path} -> {job.output_path}")
        return 0

    # Run conversions in parallel
    num_jobs = args.jobs or os.cpu_count() or 4
    num_jobs = min(num_jobs, len(jobs))
    successes = 0
    failures = 0

    with ProcessPoolExecutor(max_workers=num_jobs) as executor:
        futures = {executor.submit(run_conversion, job): job for job in jobs}
        for future in as_completed(futures):
            path, success, msg = future.result()
            if success:
                successes += 1
                print(f"  ✓ {path.name}")
            else:
                failures += 1
                print(f"  ✗ {path.name}: {msg}", file=sys.stderr)

    print(f"\nDone: {successes} converted, {failures} failed.")
    return 1 if failures > 0 else 0
