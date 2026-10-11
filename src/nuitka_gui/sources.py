"""Working out which Python file and output folder the window should offer."""

from pathlib import Path

from nuitka_gui import safe_value


def main_roots(out_dir: str, launch: Path) -> list[Path]:
    """Folders worth probing for a main.py, most specific first.

    A typed output path is probed together with its parent, because that
    path is usually the build folder, where src and dist sit side by side
    one level up. A path that names a file is read as its folder.
    """
    roots: list[Path] = []
    out = safe_value(out_dir.strip())
    if out != '':
        root = Path(out)
        if root.suffix != '':
            root = root.parent
        roots.append(root)
        if root.parent not in roots:
            roots.append(root.parent)
    if launch not in roots:
        roots.append(launch)
    return roots


def find_main(out_dir: str, launch: Path) -> str:
    """The first main.py worth offering, or "" when there is none.

    Each root is probed directly, then its "src" folder is walked so a
    main.py nested inside a package is still found. Shallow matches win, so
    the outermost main.py is preferred, and the typed path comes first.
    """
    for root in main_roots(out_dir, launch):
        direct = root / 'main.py'
        if direct.is_file():
            return str(direct.resolve())
        src = root / 'src'
        if src.is_dir():
            try:
                found = sorted(src.rglob('main.py'), key=lambda p: (len(p.parts), str(p)))
            except OSError:
                continue
            if found:
                return str(found[0].resolve())
    return ''


def default_output(launch: Path) -> str:
    """The output folder to offer, or "" when there is nothing to offer.

    Only a dist folder that already exists is proposed, so the field is not
    filled in with a folder that would then have to be created.
    """
    candidate = launch / 'dist'
    return str(candidate) if candidate.is_dir() else ''
