import os
import sys

HERE = os.path.dirname(__file__)
SITE_ROOT = os.path.dirname(HERE)

if SITE_ROOT not in sys.path:
    sys.path.insert(0, SITE_ROOT)

from render_vtps.cli import main

if __name__ == "__main__":
    main()
