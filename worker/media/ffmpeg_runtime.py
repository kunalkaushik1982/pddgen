from __future__ import annotations

import shutil
import subprocess


def find_tool(name: str) -> str | None:
    return shutil.which(name)


def run_command(command: list[str], *, timeout_seconds: float | None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
