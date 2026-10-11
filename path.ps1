[CmdletBinding(DefaultParameterSetName = 'Add')]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Path,

    [Parameter(ParameterSetName = 'Add')]
    [switch]$Add,

    [Parameter(ParameterSetName = 'Remove')]
    [switch]$Remove
)

$target = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path

$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$entries = $userPath -split ';' | Where-Object { $_ -ne '' }

if ($Remove) {
    if ($entries -notcontains $target) {
        Write-Host "Not in PATH: $target"
        return
    }

    $newPath = (($entries | Where-Object { $_ -ne $target }) -join ';')
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')

    $env:Path = ($env:Path -split ';' | Where-Object { $_ -ne $target }) -join ';'

    Write-Host "Removed from PATH: $target"
} else {
    if ($entries -contains $target) {
        Write-Host "Already in PATH: $target"
        return
    }

    $newPath = (($entries + $target) -join ';')
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')

    $env:Path = "$env:Path;$target"

    Write-Host "Added to PATH: $target"
}
