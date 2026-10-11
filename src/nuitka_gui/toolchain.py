"""Locating the toolchain that will run the build.

The build is run through ``uv run`` in the project's folder, so it uses the
environment the project was set up in rather than whatever happens to be on
PATH. A shell is used because uv is not always a real executable: a pip
install leaves a ``.cmd`` shim behind, which only a shell can start.
"""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import QObject, QProcess, QStandardPaths


@dataclass(frozen=True)
class Plugin:
    """One plugin Nuitka offers, as "--plugin-list" printed it."""

    name: str
    description: str


def _find_executable(name: str, missing: str) -> str:
    found = QStandardPaths.findExecutable(name)
    if found == "":
        raise FileNotFoundError(missing)
    return found


def find_shell() -> str:
    """The PowerShell to run the build with, preferring version 7."""
    for name in ("pwsh", "powershell"):
        found = QStandardPaths.findExecutable(name)
        if found != "":
            return found
    raise FileNotFoundError("No PowerShell found on PATH, so Nuitka cannot be run.")


def find_uv() -> str:
    """The uv executable that will run Nuitka in the project venv."""
    return _find_executable("uv", "No uv found on PATH.")


def quote_ps(text: str) -> str:
    """One argument as PowerShell code, so that spaces survive it."""
    return "'" + text.replace("'", "''") + "'"


def nuitka_command(args: Sequence[str]) -> list[str]:
    """The whole command that runs Nuitka with these arguments."""
    shell = find_shell()
    uv = find_uv()
    script = f"& {quote_ps(uv)} --no-progress run python -m nuitka"
    if args:
        script += " " + " ".join(quote_ps(arg) for arg in args)
    return [shell, "-NoProfile", "-Command", script]


def list_plugins(parent: QObject | None = None) -> list[Plugin]:
    """The plugins the resolved Nuitka has.

    Raises FileNotFoundError when the toolchain is missing and TimeoutError
    when the listing cannot be obtained. An empty list means the run worked
    and Nuitka really has nothing to offer.
    """
    command = nuitka_command(["--plugin-list"])
    proc = QProcess(parent)
    proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    proc.start(command[0], command[1:])
    if not proc.waitForStarted(10000):
        raise TimeoutError("Could not start Nuitka to list plugins.")
    if not proc.waitForFinished(60000):
        proc.kill()
        _ = proc.waitForFinished(5000)
        raise TimeoutError("Timed out asking Nuitka for plugins.")
    raw = bytes(proc.readAllStandardOutput().data()).decode("utf-8", "replace")
    return parse_plugins(raw)


def parse_plugins(output: str) -> list[Plugin]:
    """Pull the plugins out of "--plugin-list" output.

    Plugin lines are "name<padding>description"; the padding is what tells
    them apart from the banner text above them.
    """
    plugins: list[Plugin] = []
    for raw in output.splitlines():
        name, sep, rest = raw.strip().partition("  ")
        name = name.strip()
        if sep == "" or name == "" or " " in name:
            continue
        plugins.append(Plugin(name, rest.strip()))
    return plugins


def show_command(argv: Sequence[str]) -> str:
    """The command as a copyable line, the way Windows was handed it."""
    return subprocess.list2cmdline(argv)
