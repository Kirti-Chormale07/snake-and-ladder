"""Allow ``python -m snake_ladder`` to launch the CLI."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
