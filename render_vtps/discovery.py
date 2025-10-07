
"""Filesystem discovery for time directories and VTP files."""
from __future__ import annotations

import os
import re
from typing import List, Sequence, Tuple

from .utils import basename_list


_TIME_DIR_RE = re.compile(r"^[0-9]+(\.[0-9]+)?$")


def find_vtp_files(time_dirs_path: str) -> Tuple[List[str], List[str]]:
    """Return sorted (time_dirs, vtp_files) within *time_dirs_path*.

    *time_dirs* are directories whose names match floating-point numbers.
    *vtp_files* are all .vtp files found under those directories.
    """
    vtp_files: List[str] = []
    time_dirs: List[str] = []

    for item in os.listdir(time_dirs_path):
        full_path = os.path.join(time_dirs_path, item)
        if os.path.isdir(full_path) and _TIME_DIR_RE.match(item):
            time_dirs.append(full_path)
            for root, _dirs, files in os.walk(full_path):
                for file in files:
                    if file.endswith(".vtp") or file.endswith(".vtk"):
                        vtp_files.append(os.path.join(root, file))

    time_dirs.sort(key=lambda f: float(os.path.basename(f)))
    vtp_files.sort()
    return time_dirs, vtp_files


def validate_vtp_file(vtp_filename: str | None, vtp_files: Sequence[str]) -> str:
    """Validate that *vtp_filename* exists among *vtp_files* or choose first.

    Returns:
        The selected VTP file **basename**.

    Raises:
        FileNotFoundError: If *vtp_files* is empty.
        ValueError: If *vtp_filename* is provided but not found.
    """
    if vtp_filename:
        if vtp_filename not in basename_list(vtp_files):
            raise ValueError(
                f"Specified VTP file '{vtp_filename}' not found in any time directory."
            )
        return vtp_filename

    if not vtp_files:
        raise FileNotFoundError("No VTP files found in the specified time directories.")

    return os.path.basename(vtp_files[0])
