# Nuitka GUI

A small PySide6 desktop front end for compiling Python programs with
[Nuitka](https://nuitka.net/). Fill in the fields, and the app assembles the
Nuitka command line for you, runs it in your project's `uv` environment, and
streams the output live.

## Features

- **One command line, built for you.** Pick your script, output folder and exe
  name; the app turns them into a single `nuitka` invocation.
- **Checkbox options.** Common Nuitka flags such as `--onefile`,
  `--standalone`, `--windows-console-mode=disable`, `--msvc=latest`, `--zig`,
  `--low-memory`, and more, with sensible defaults.
- **Guarded C backends.** `--zig` and `--msvc=latest` cannot both be on, and
  the app warns you if they are.
- **Optional admin elevation.** `--windows-uac-admin` makes the built exe ask
  for admin rights through a UAC prompt every time it starts. Off by default.
- **Data files.** Include a single file or a whole folder via
  `--include-data-files` / `--include-data-dir`, with an optional destination
  name inside the app.
- **Plugin picker.** Lists the plugins your installed Nuitka offers and lets you
  tick the ones to enable.
- **Icon support.** Take the app icon from a `.ico` or another `.exe`.
- **Job count sized to your machine.** Defaults to a core count capped by
  available RAM, since each C compiler process can hold hundreds of MB.
- **Live build log.** Output follows the build while you are at the bottom and
  stays put once you scroll up.
- **Cancellable builds.** Cancel kills the whole process tree (Nuitka's `cl.exe`
  and Scons children included), not just the direct child.
- **Frozen-build fix.** Works around a PySide6 signal patch that otherwise
  segfaults the Nuitka-compiled app on the first `QProcess` signal.

## Requirements

- Windows
- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- PySide6 6.12+
- Nuitka (installed into the project environment)

The app runs Nuitka through `uv run` in the folder it was launched from, so the
build uses that project's environment rather than whatever is on `PATH`.

## Installation

The GUI is meant to be used as a built executable, not run from source. Build it
once, then put it somewhere on your `PATH`.

1. Set up the virtual environment and sync dependencies:

   ```powershell
   .\init.ps1
   ```

   or

   ```powershell
   # OR
   uv venv .\.venv
   uv sync
   ```

2. Install Nuitka into the environment:

   ```powershell
   .\nuitka.ps1
   ```

   or

   ```powershell
   $nuitka = Test-Path '.\.venv\Scripts\nuitka.cmd'
   if (-not $nuitka) {
       uv pip install pip
       uv --no-progress run python -m pip install "Nuitka[all]"
   } else {
       Write-Host "nuitka is installed"
   }
   ```

3. Build the executable:

   ```powershell
   .\build.ps1

   ```

   or

   ```powershell
   uv --no-progress run python -m nuitka `
    --onefile `
    --low-memory `
    --remove-output `
    --windows-console-mode=disable `
    --zig ` # Replace '--zig' with '--msvc=latest' if zig throws an error
    --assume-yes-for-downloads `
    --include-windows-runtime-dlls=yes `
    --enable-plugin=pyside6 `
    --windows-icon-from-ico=assets/icon.ico  `
    --output-dir=dist `
    --output-filename=nuitka-gui.exe `
    .\src\nuitka_gui\main.py
   ```

   This wraps Nuitka with `--onefile`, the PySide6 plugin, the app icon and the
   Windows runtime DLLs, writing `dist\nuitka-gui.exe`.

4. Copy the executable into a folder that is on your `PATH`, so you can call it
   from any project. For example:

   ```powershell
   $gui = "$env:LOCALAPPDATA\NuitkaGui"
   New-Item -ItemType Directory -Force -Path $gui
   Copy-Item .\dist\nuitka-gui.exe -Destination $gui -Force
   ```

   Add `$gui` to `PATH` if it is not already there.

## Usage

Run the executable from the folder of the project you want to compile, so the
build picks up that project's environment:

```powershell
cd C:\path\to\the\project\to\compile
# Or launch terminal from project directory
nuitka-gui
```

The app works out of its launch directory, so it looks for `main.py` and a `dist`
folder there and runs Nuitka through `uv run` inside that project.

Then, in the window:

1. **Select a Python file** — the entry script to compile (e.g. `main.py`). The
   app probes the output folder and its `src` directory to pre-fill this.
2. **Select an output directory** — defaults to a `dist` folder next to the
   launch directory when one exists.
3. **Set the exe name** — defaults to the script's own name.
4. **Choose options** — tick the Nuitka flags you want, or leave the defaults.
5. **Add data** — optionally include a file or folder and name it inside the app.
6. **Pick plugins / an icon** — as needed.
7. **Set the job count** — `Jobs Auto` uses one per core, capped by RAM.
8. Click **Compile**, and watch the log. **Cancel** stops the build.

The generated `nuitka` command is written to the log so you can copy and rerun
it yourself.

## Project layout

```
src/nuitka_gui/
  __init__.py        Public API and version
  main.py            Entry point; restores PySide6 signal methods when frozen
  ui/                Everything the user sees
    gui.py           The main window and its wiring
    logview.py       The auto-following build log pane
    plugindialog.py  The plugin picker popup
  build/             Turning the fields into a command line and running it
    commandline.py   Turns window state into one Nuitka argument list (no Qt)
    options.py       The checkbox catalog and which ones start enabled
    buildproc.py     Runs the build as a child process and stops it again
    toolchain.py     Finds the shell, uv and Nuitka; lists plugins
  system/            Probing the machine and locating files
    host.py          RAM and core counts for the job default
    sources.py       Guesses the entry script and default output folder
assets/
  icon.ico           Application icon
```

The modules that decide what the command line looks like (`build/commandline.py`,
`build/options.py`, `system/host.py`, `system/sources.py`) do not touch Qt, so
their behaviour can be checked with a plain test.

## Scripts

| Script       | Purpose                                            |
| ------------ | -------------------------------------------------- |
| `init.ps1`   | Create the `.venv` and sync dependencies.          |
| `nuitka.ps1` | Install Nuitka into the project environment.       |
| `build.ps1`  | Compile the GUI itself into `dist/nuitka-gui.exe`. |

## License

No license has been specified for this project yet.
