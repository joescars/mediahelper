"""Interactive terminal picker for files and folders."""

from __future__ import annotations

import atexit
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from rich.panel import Panel
from rich.text import Text

from mediahelper.theme import console, AMBER, AMBER_DIM, AMBER_BRIGHT, ORANGE, BORDER_STYLE


_saved_termios = None


def _save_terminal_state() -> None:
    """Save terminal settings so they can be restored on exit."""
    global _saved_termios
    if os.name != "nt" and sys.stdin.isatty():
        import termios
        _saved_termios = termios.tcgetattr(sys.stdin.fileno())


def _restore_terminal_state() -> None:
    """Restore terminal to its original state."""
    if _saved_termios is not None:
        import termios
        try:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _saved_termios)
        except Exception:
            pass


@dataclass(frozen=True)
class PickerEntry:
    """Single row in the interactive picker UI."""

    path: Path
    label: str
    selectable: bool
    navigable: bool


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
                f"DIR  {directory.name}/",
                selectable=True,
                navigable=True,
            )
        )

    for file_path in files:
        if file_extensions and file_path.suffix.lower() not in file_extensions:
            continue
        entries.append(PickerEntry(file_path, f"     {file_path.name}", selectable=True, navigable=False))

    return entries


def _render(current_dir: Path, entries: list[PickerEntry], cursor: int, selected: set[Path]) -> None:
    console.clear()

    body = Text()

    path_label = Text("  >> ", style=AMBER)
    path_label.append(str(current_dir), style=f"bold {AMBER_BRIGHT}")
    body.append_text(path_label)
    body.append("\n")

    selected_label = Text(f"  Selected: {len(selected)}", style=ORANGE)
    body.append_text(selected_label)
    body.append("\n\n")

    if not entries:
        body.append("  (empty directory)\n", style=AMBER_DIM)
    else:
        for idx, entry in enumerate(entries):
            is_cursor = idx == cursor
            is_selected = entry.path in selected

            if is_cursor:
                pointer = Text(" >> ", style=f"bold {AMBER_BRIGHT}")
            else:
                pointer = Text("   ", style=AMBER_DIM)
            body.append_text(pointer)

            if entry.selectable:
                if is_selected:
                    marker = Text("[x] ", style=f"bold {AMBER_BRIGHT}")
                else:
                    marker = Text("[ ] ", style=AMBER_DIM)
            else:
                marker = Text("  ")
            body.append_text(marker)

            if is_cursor:
                label_style = f"bold {AMBER_BRIGHT}"
            elif is_selected:
                label_style = AMBER
            else:
                label_style = AMBER_DIM
            body.append(entry.label, style=label_style)
            body.append("\n")

    keys = Text(
        "  ↑↓ move · ←→ navigate · Space select · A all · S start · Q quit",
        style=AMBER_DIM,
    )

    panel = Panel(
        body,
        title="[bold]== MEDIAHELPER ==[/bold]",
        title_align="center",
        subtitle=keys,
        subtitle_align="center",
        border_style=BORDER_STYLE,
        padding=(0, 1),
    )
    console.print(panel)


def interactive_select_option(
    title: str,
    options: list[tuple[str, str]],
) -> str | None:
    """
    Present a single-choice menu. Each option is (value, label).

    Returns the selected value, or None on cancel.
    """
    cursor = 0
    _save_terminal_state()
    atexit.register(_restore_terminal_state)

    while True:
        console.clear()
        body = Text()
        body.append("\n")

        for idx, (_value, label) in enumerate(options):
            is_cursor = idx == cursor
            if is_cursor:
                body.append("  >> ", style=f"bold {AMBER_BRIGHT}")
                body.append(label, style=f"bold {AMBER_BRIGHT}")
            else:
                body.append("    ", style=AMBER_DIM)
                body.append(label, style=AMBER_DIM)
            body.append("\n")

        body.append("\n")

        keys = Text("  ↑↓ move · Enter select · Q cancel", style=AMBER_DIM)

        panel = Panel(
            body,
            title=f"[bold]{title}[/bold]",
            title_align="center",
            subtitle=keys,
            subtitle_align="center",
            border_style=BORDER_STYLE,
            padding=(0, 1),
        )
        console.print(panel)

        key = _read_key()
        if key == "up":
            cursor = (cursor - 1) % len(options)
        elif key == "down":
            cursor = (cursor + 1) % len(options)
        elif key == "enter":
            console.clear()
            return options[cursor][0]
        elif key in ("q", "esc"):
            console.clear()
            return None


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
    _save_terminal_state()
    atexit.register(_restore_terminal_state)

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
            console.clear()
            return [str(path) for path in sorted(selected, key=lambda p: str(p).lower())]
        elif key in ("q", "esc"):
            console.clear()
            return []
