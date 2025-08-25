
import os
import shutil
import subprocess
import sys

from pathlib import Path


def main() -> int:
    """CLI entry point that invokes ParaView's pvpython.

    It looks for pvpython in the following order:
      1) $PVPYTHON environment variable
      2) 'pvpython' found on PATH

    Then runs: pvpython _pv_entry.py <args...>
    """
    pvpython = os.environ.get("PVPYTHON") or "pvpython"
    if shutil.which(pvpython) is None:
        sys.stderr.write(
            "Error: pvpython not found. Set the PVPYTHON env var or ensure 'pvpython' is on PATH.\n"
        )
        return 127

    entry = Path(__file__).resolve().parent / "_pv_entry.py"
    cmd = [pvpython, str(entry), *sys.argv[1:]]
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        return 130
