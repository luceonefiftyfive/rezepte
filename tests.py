#!/usr/bin/env python3
"""Run all backend and frontend tests from the repository root."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent


def run_tests(directory: str, command: list[str]) -> int:
    print(f"\n==> {directory}: {' '.join(command)}")
    return subprocess.run(command, cwd=ROOT_DIR / directory, check=False).returncode


def main() -> int:
    required_commands = ("uv", "npm")
    missing_commands = [
        command for command in required_commands if shutil.which(command) is None
    ]
    if missing_commands:
        print(
            f"Missing required command(s): {', '.join(missing_commands)}",
            file=sys.stderr,
        )
        return 1

    if run_tests("backend", ["uv", "run", "pytest"]) != 0:
        return 1
    return run_tests("frontend", ["npm", "test"])


if __name__ == "__main__":
    raise SystemExit(main())
