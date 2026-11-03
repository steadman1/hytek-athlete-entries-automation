"""Robust swim time parsing into centiseconds (hundredths of a second).

Team Manager stores entry times in the `ENTRY.Score` integer column as centiseconds:
    58.69s  -> 5869
    1:01.01 -> 6101
    23.5    -> 2350
    0.0     -> 0 (No Time / NT)
"""
from __future__ import annotations

import math
import re
from typing import Optional


# Deterministic regex patterns for common swim time formats:
# 1) MM:SS.cc  or  M:SS.cc (e.g. "1:01.01", "01:23.45", "4:32.10", "15:45.00")
_PATTERN_MM_SS_CC = re.compile(
    r"^\s*(?P<m>\d{1,2}):(?P<s>\d{2})(?:[.:](?P<c>\d{1,3}))?\s*$"
)

# 2) SS.cc (e.g. "23.69", "58.69", "48.00", "23.5", "23")
_PATTERN_SS_CC = re.compile(
    r"^\s*(?P<s>\d{1,3})(?:[.:](?P<c>\d{1,3}))?\s*$"
)

# 3) Plain "NT", "NONE", "NO TIME", "-", "" -> 0 centiseconds
_PATTERN_NT = re.compile(
    r"^\s*(?:nt|no\s*time|none|n/a|-|0|0\.0|0:00|00:00\.00)?\s*$",
    re.IGNORECASE,
)


def _pad_centiseconds(raw_c: Optional[str]) -> int:
    """Convert raw centisecond / millisecond digits into 2-digit centiseconds (0-99)."""
    if not raw_c:
        return 0
    # Strip any extra dots/colons
    clean = raw_c.strip()
    if len(clean) == 1:
        return int(clean) * 10
    elif len(clean) == 2:
        return int(clean)
    else:
        # e.g. "123" -> 12 centiseconds (rounded)
        return int(round(int(clean[:3]) / 10.0))


def parse_time_to_centiseconds(raw: Optional[str | float | int]) -> int:
    """Parse a raw swim time into integer centiseconds.

    Returns:
        int: centiseconds (e.g. 5869). Returns 0 for No-Time (NT).

    Raises:
        ValueError: if the string cannot be parsed as a reasonable swim time.
    """
    if raw is None:
        return 0

    if isinstance(raw, (int, float)):
        if math.isnan(raw):
            return 0
        if raw == 0:
            return 0
        # If passed a float like 58.69 -> 5869
        return int(round(float(raw) * 100))

    s = str(raw).strip()
    if not s or _PATTERN_NT.match(s):
        return 0

    # Strip trailing course letters like "Y", "S", "L" if present (e.g. "58.69Y")
    s = re.sub(r"[A-Za-z]+$", "", s).strip()

    # Try MM:SS.cc / M:SS:cc
    m = _PATTERN_MM_SS_CC.match(s)
    if m:
        minutes = int(m.group("m"))
        seconds = int(m.group("s"))
        cs = _pad_centiseconds(m.group("c"))
        total = (minutes * 60 + seconds) * 100 + cs
        return total

    # Try SS.cc / SS:cc
    m = _PATTERN_SS_CC.match(s)
    if m:
        seconds = int(m.group("s"))
        cs = _pad_centiseconds(m.group("c"))
        total = seconds * 100 + cs
        return total

    raise ValueError(f"Unable to parse swim time: {raw!r}")


def format_centiseconds(cs: int) -> str:
    """Format centiseconds back into standard swim format (e.g. 5869 -> '58.69', 6101 -> '1:01.01')."""
    if cs <= 0:
        return "NT"
    total_seconds = cs / 100.0
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    if minutes > 0:
        return f"{minutes}:{seconds:05.2f}"
    return f"{seconds:.2f}"
