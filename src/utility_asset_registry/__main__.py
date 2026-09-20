"""Allow `python -m utility_asset_registry load` / `start` / `run` / `setup` / `check` / `rejects`."""

import sys

from utility_asset_registry.cli import OPERATOR_COMMANDS, operator_app, run

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in OPERATOR_COMMANDS:
        operator_app()
    else:
        run()
