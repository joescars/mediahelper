"""Interactive terminal picker for files and folders."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PickerEntry:
    """Single row in the interactive picker UI."""

    path: Path
    label: str
    selectable: bool
    navigable: bool


def _clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _read_key() -> str:
    if os.name == "nt":
        import msvcrt

        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            code = msvcrt.getwch()
            return {
                "H": "up",
                "P": "down",
                "K": "left",
                "M": "right",
            }.get(code, "unknown")
        return {
            " ": "space",
            "\r": "enter",
            "\n": "enter",
            "\x1b": "esc",
            "q": "q",
            "Q": "q",
            "s": "submit",
            "S": "submit",
            "a": "select_all",
            "A": "select_all",
        }.get(ch, "unknown")

    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            seq = sys.stdin.read(2)
            if seq == "[A":
                return "up"
            if seq == "[B":
                return "down"
            if seq == "[C":
                return "right"
            if seq == "[D":
                return "left"
            return "esc"
        return {
            " ": "space",
            "\r": "enter",
            "\n": "enter",
            "q": "q",
            "Q": "q",
            "s": "submit",
            "S": "submit",
            "a": "select_all",
            "A": "select_all",
        }.get(ch, "unknown")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _list_entries(current_dir: Path, file_extensions: set[str] | None) -> list[PickerEntry]:
    entries: list[PickerEntry] = []

    if current_dir.parent != current_dir:
        entries.append(PickerEntry(current_dir.parent, "..", selectable=False, navigable=True))

    directories = sorted([p for p in current_dir.iterdir() if p.is_dir()], key=lambda p: p.name.lower())
    files = sorted([p for p in current_dir.iterdir() if p.is_file()], key=lambda p: p.name.lower())

    for directory in directories:
        entries.append(
            PickerEntry(
                directory,
                f"[DIR] {directory.name}{os.sep}",
                selectable=True,
                navigable=True,
            )
        )

    for file_path in files:
        if file_extensions and file_path.suffix.lower() not in file_extensions:
            continue
        entries.append(PickerEntry(file_path, file_path.name, selectable=True, navigable=False))

    return entries


def _render(current_dir: Path, entries: list[PickerEntry], cursor: int, selected: set[Path]) -> None:
    _clear_screen()
    print("MediaHelper Interactive Picker")
    print(f"Current: {current_dir}")
    print("Keys: Up/Down move  Enter/Right open  Left up  Space select  A select visible  S start  Q cancel")
    print(f"Selected: {len(selected)}")
    print()

    if not entries:
        print("  (No files or directories here)")
        return

    for idx, entry in enumerate(entries):
        pointer = ">" if idx == cursor else " "
        marker = "[x]" if entry.path in selected else "[ ]"
        if not entry.selectable:
            marker = "   "
        print(f"{pointer} {marker} {entry.label}")


def interactive_select_paths(
    start_dir: str | Path | None = None,
    file_extensions: set[str] | None = None,
) -> list[str]:
    """
    Let users select files and/or directories from a terminal explorer UI.

    Returns selected absolute paths as strings. Returns empty list on cancel.
    """
    current_dir = Path(start_dir).resolve() if start_dir else Path.cwd().resolve()
    selected: set[Path] = set()
    cursor = 0

    while True:
        try:
            entries = _list_entries(current_dir, file_extensions)
        except PermissionError:
            current_dir = current_dir.parent
            entries = _list_entries(current_dir, file_extensions)

        if entries:
            cursor = max(0, min(cursor, len(entries) - 1))
        else:
            cursor = 0

        _render(current_dir, entries, cursor, selected)

        key = _read_key()
        if key == "up" and entries:
            cursor = (cursor - 1) % len(entries)
        elif key == "down" and entries:
            cursor = (cursor + 1) % len(entries)
        elif key in ("enter", "right") and entries:
            entry = entries[cursor]
            if entry.navigable:
                current_dir = entry.path.resolve()
                cursor = 0
        elif key == "left":
            if current_dir.parent != current_dir:
                current_dir = current_dir.parent
                cursor = 0
        elif key == "space" and entries:
            entry = entries[cursor]
            if entry.selectable:
                if entry.path in selected:
                    selected.remove(entry.path)
                else:
                    selected.add(entry.path)
        elif key == "select_all":
            for entry in entries:
                if entry.selectable:
                    selected.add(entry.path)
        elif key == "submit":
            _clear_screen()
            return [str(path) for path in sorted(selected, key=lambda p: str(p).lower())]
        elif key in ("q", "esc"):
            _clear_screen()
            return []
