"""The option catalog the window offers, and which ones start enabled."""

# Every checkbox the window shows, in display order. Two of them are C
# backends and cannot both be on, so only one of them starts enabled.
build_args: tuple[str, ...] = (
    "--onefile",
    "--standalone",
    "--windows-console-mode=disable",
    # C backend: pick exactly one, Nuitka rejects "--zig" with "--msvc".
    "--zig",
    "--msvc=latest",
    # Empties "__doc__", which breaks argparse/click help.
    "--python-flag=no_docstrings",
    # Asserts are compiled out, so there is less C to translate.
    "--python-flag=no_asserts",
    # Single threaded zstd level 3 instead of level 22: faster packing.
    "--low-memory",
    "--assume-yes-for-downloads",
    "--onefile-no-compression",
    "--include-windows-runtime-dlls=yes",
    # Drops the build directory afterwards, trading build cache for disk.
    "--remove-output",
    "--reports",
)

# MSVC is the default because cl.exe uses far less memory than zig. The rest
# are trade-offs that stay off unless a build needs them.
off_by_default: frozenset[str] = frozenset(
    {"--standalone", "--zig", "--onefile-no-compression", "--reports"}
)

# The two shapes of "extra file for the app", switched by one button.
data_args: tuple[str, ...] = ("--include-data-files", "--include-data-dir")
