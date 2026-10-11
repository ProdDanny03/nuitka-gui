$nuitka = Test-Path '.\.venv\Scripts\nuitka.cmd'

if (-not $nuitka) {
    uv pip install pip
    uv --no-progress run python -m pip install "Nuitka[all]"
} else {
    Write-Host "nuitka is installed"
}
