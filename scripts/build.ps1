uv run nuitka `
    --onefile `
    --low-memory `
    --remove-output `
    --windows-console-mode=disable `
    --zig `
    --assume-yes-for-downloads `
    --include-windows-runtime-dlls=yes `
    --enable-plugin=pyside6 `
    --windows-icon-from-ico=assets/icon.ico  `
    --output-dir=dist `
    --output-filename=nuitka-gui.exe `
    .\src\nuitka_gui\main.py
