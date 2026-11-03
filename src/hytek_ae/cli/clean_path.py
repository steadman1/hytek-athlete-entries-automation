"""Custom Click ParamTypes and path cleaning utilities."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

import click


def clean_path_string(value: Any) -> str:
    """Strip whitespace and surrounding single or double quotes, and unescape spaces.
    Handles terminal drag-and-drop artifacts like:
      " '/Users/.../file.csv' "
      '\"/Users/.../file.csv\"'
      "/Users/.../My\\ File.csv"
    """
    if value is None:
        return ""
    s = str(value).strip()

    # Repeatedly strip outer quotes and whitespace (handles nested quotes or spaces)
    while len(s) >= 2 and ((s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"'))):
        s = s[1:-1].strip()

    # Handle shell backslash-escaped spaces (e.g. from macOS/Linux drag-and-drop: My\ File.csv)
    # Don't replace Windows backslashes in paths like C:\Users\...
    if "\\ " in s:
        s = s.replace("\\ ", " ")

    return s


class CleanPath(click.ParamType):
    """Click ParamType that sanitizes quoted/whitespace-padded path inputs."""

    name = "clean_path"

    def __init__(
        self,
        exists: bool = False,
        file_okay: bool = True,
        dir_okay: bool = False,
        readable: bool = True,
    ) -> None:
        self.exists = exists
        self.file_okay = file_okay
        self.dir_okay = dir_okay
        self.readable = readable

    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> Path:
        if isinstance(value, Path):
            p = value
        else:
            cleaned = clean_path_string(value)
            p = Path(cleaned).expanduser()

        if self.exists and not p.exists():
            self.fail(f"Path '{p}' does not exist.", param, ctx)
        if not self.file_okay and p.is_file():
            self.fail(f"Path '{p}' is a file.", param, ctx)
        if not self.dir_okay and p.is_dir():
            self.fail(f"Path '{p}' is a directory.", param, ctx)

        return p
