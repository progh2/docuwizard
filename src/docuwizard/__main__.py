"""Application entrypoint."""

from __future__ import annotations

import sys


def main() -> int:
    """Launch DocuWizard GUI (stub until full UI is implemented)."""
    from docuwizard.app import run

    return run()


if __name__ == "__main__":
    sys.exit(main())
