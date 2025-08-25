
"""Utility helpers for argument parsing and validation."""
from __future__ import annotations

import re
from typing import Iterable, List, Optional, Tuple


def parse_fixed_range(rng: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    """Parse a fixed color range string like "min,max" or "min:max".

    Raises:
        ValueError: If the string is not in a valid format or min >= max.
    """
    if rng is None:
        return None, None
    tokens = re.split(r"[,:]+", str(rng).strip())
    if len(tokens) != 2:
        raise ValueError(
            f"Invalid --range '{rng}'. Use 'min,max' or 'min:max'.")
    cmin, cmax = float(tokens[0]), float(tokens[1])
    if not (cmin < cmax):
        raise ValueError(
            f"--range requires min < max (got {cmin} and {cmax}).")
    return cmin, cmax


def parse_render_size(size: str) -> Tuple[int, int]:
    """Parse a render size string like "1280x720" into a tuple."""
    try:
        w, h = (int(x) for x in str(size).lower().split("x", 1))
        return w, h
    except Exception as exc:  # noqa: BLE001
        raise ValueError(
            f"Invalid --render_size '{size}'. Expected 'WxH'.") from exc


def parse_camera_view_point(val: str | None) -> Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]] | None:
    """Parse a camera vector list of 9 numbers: pos(3), focal(3), up(3)."""
    if not val:
        return None
    s = str(val).strip().strip("[](){}")
    nums = [float(x) for x in re.split(r"[\s,]+", s) if x]
    if len(nums) != 9:
        raise ValueError("--camera_view_point must provide exactly 9 numbers.")
    pos = tuple(nums[0:3])
    focal = tuple(nums[3:6])
    up = tuple(nums[6:9])
    return pos, focal, up


def basename_list(paths: Iterable[str]) -> List[str]:
    from os.path import basename
    return [basename(p) for p in paths]
