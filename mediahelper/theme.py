"""Shared terminal theme for the retro CRT amber look."""

from rich.console import Console
from rich.theme import Theme

AMBER = "#FFB000"
AMBER_DIM = "#B8860B"
AMBER_BRIGHT = "#FFD700"
ORANGE = "#FF8C00"

theme = Theme({
    "title": f"bold {AMBER_BRIGHT}",
    "heading": f"bold {AMBER}",
    "info": AMBER,
    "dim": AMBER_DIM,
    "accent": ORANGE,
    "success": f"bold {AMBER_BRIGHT}",
    "error": f"bold red",
    "highlight": f"bold reverse {AMBER}",
})

console = Console(theme=theme, highlight=False)

BORDER_STYLE = AMBER_DIM
TITLE_STYLE = f"bold {AMBER_BRIGHT}"
