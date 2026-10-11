"""Turning what the window holds into one Nuitka command line.

None of this touches Qt: it takes values and gives back arguments, which
keeps the many ways it can be wrong reachable from a plain test.
"""

import shlex
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class BuildRequest:
    """One build as the window currently describes it.

    Every field is the raw text of a control; it is cleaned here, so the
    argument list and the file paths cannot disagree.
    """

    script: str = ""
    out_dir: str = ""
    exe_name: str = ""
    data_source: str = ""
    data_dest: str = ""
    data_flag: str = "--include-data-files"
    plugins: Collection[str] = ()
    icon_arg: str = ""
    extra_args: str = ""
    jobs: int = 0
    flags: Collection[str] = field(default_factory=tuple)


def safe_value(text: str) -> str:
    """Field text that is safe to embed in a single build argument.

    Nuitka reads its command line with the MSVCRT rules, where a double
    quote is a quoting character rather than data. Quotes wrapped around the
    whole value come from a copy and paste, so they go; any left inside are
    replaced with single quotes, which keeps the text visible.
    """
    return text.strip('"').replace('"', "'")


def split_args(text: str) -> list[str]:
    """Split the free text box the way Nuitka's own parser would.

    The MSVCRT rules are close enough to POSIX shlex for the everyday cases,
    with escapes off, because a Windows path is full of backslashes that
    must survive.
    """
    lexer = shlex.shlex(text, posix=True)
    lexer.whitespace_split = True
    lexer.escape = ""
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        # An unbalanced quote makes shlex give up, and the raw words are
        # then passed on with whatever quotes they carry.
        return [safe_value(word) for word in text.split()]


def output_name(request: BuildRequest) -> str:
    """The exe name, or "" when there is nothing to call it yet.

    A name typed with or without the extension means the same thing, and an
    empty field falls back to the script's own name.
    """
    name = safe_value(request.exe_name.strip())
    if name.lower().endswith(".exe"):
        name = name[: -len(".exe")]
    if name == "":
        script = safe_value(request.script.strip())
        if script != "":
            name = Path(script).stem
    return name


def data_name(path: str) -> str:
    """The last name in a path, whichever separator it was typed with.

    A trailing separator goes first, so a folder pasted out of Explorer
    keeps its own name. A drive root has no last name, and "" says so.
    """
    trimmed = path.rstrip("\\/")
    if trimmed.endswith(":"):
        return ""
    return trimmed.replace("/", "\\").rsplit("\\", 1)[-1]


def data_fields(source: str, dest: str) -> tuple[str, str]:
    """The two data fields as one source and one destination, cleaned up.

    A source pasted as source=destination is split here, so the older one
    field form still works; the destination it came with is used only when
    the destination field is empty. An empty destination falls back to the
    last name in the source.
    """
    text = safe_value(source.strip())
    target = safe_value(dest.strip())
    if "=" in text:
        text, _, pasted = text.partition("=")
        if target == "":
            target = pasted
    path_text = text.strip().rstrip("\\/")
    if target == "":
        target = data_name(path_text)
    return path_text, target.strip()


def data_value(source: str, dest: str) -> str:
    """The data fields as the single value Nuitka wants, or "".

    A source with no name of its own to be renamed to, such as a drive
    root, yields nothing, since no destination could be written for it.
    """
    path_text, target = data_fields(source, dest)
    if path_text == "" or target == "":
        return ""
    return f"{path_text}={target}"


def data_problem(source: str, dest: str, flag: str, base: Path) -> str:
    """The reason the data fields cannot be used as they stand, else "".

    Both fields empty is no problem, since most builds include no data. A
    pattern is left to Nuitka. A plain path is checked, because the two
    things worth catching are a path that is not there and a folder handed
    to the option that wants a single file. The path is taken relative to
    the script folder, which is the working directory the build gets.
    """
    path_text, target = data_fields(source, dest)
    if path_text == "":
        if target == "":
            return ""
        return "The destination needs a path to be taken from."
    if target.startswith(("/", "\\")) or Path(target).is_absolute():
        return "The destination is where the file lands in the app, not a path."
    if any(char in path_text for char in "*?"):
        return ""
    if data_name(path_text) == "":
        return f"{path_text} has no name of its own to use as the destination."
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    if not path.exists():
        return f"There is no file or folder at {path}."
    if flag == "--include-data-dir" and not path.is_dir():
        return "--include-data-dir takes a folder, and that path is a file."
    if flag == "--include-data-files" and path.is_dir():
        return "--include-data-files takes one file; switch to --include-data-dir."
    return ""


def icon_option(path: str) -> str:
    """The option that takes the app icon from this file, or "".

    Nuitka wants the two cases spelled differently, and only one of them may
    be given.
    """
    lowered = path.lower()
    if lowered.endswith(".ico"):
        return f"--windows-icon-from-ico={path}"
    if lowered.endswith(".exe"):
        return f"--windows-icon-from-exe={path}"
    return ""


def build_arguments(request: BuildRequest) -> list[str]:
    """The full Nuitka argument list for this build, in the order given.

    The order is not arbitrary: the flags come from the checkboxes, then the
    values that follow from the fields, and the script last, because a path
    is the one argument with spaces in it.
    """
    args = list(request.flags)
    if request.jobs > 0:
        args.append(f"--jobs={request.jobs}")
    out = safe_value(request.out_dir.strip())
    if out != "":
        args.append(f"--output-dir={out}")
    name = output_name(request)
    if name != "":
        args.append(f"--output-filename={name}.exe")
    spec = data_value(request.data_source, request.data_dest)
    if spec != "":
        args.append(f"{request.data_flag}={spec}")
    for plugin in sorted(request.plugins):
        args.append(f"--enable-plugin={plugin}")
    if request.icon_arg != "":
        args.append(request.icon_arg)
    args.extend(split_args(request.extra_args))
    script = safe_value(request.script.strip())
    if script != "":
        args.append(str(Path(script).resolve()))
    return args


def quote_notes(fields: Mapping[str, str]) -> list[str]:
    """Which fields had double quotes replaced before the build."""
    return [label for label, text in fields.items() if '"' in text]
