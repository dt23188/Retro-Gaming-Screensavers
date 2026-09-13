param([string]$InstallerPath, [switch]$Silent)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
if (-not $InstallerPath) {
    $Candidates = @(Get-ChildItem -LiteralPath "$Root\releases" -Filter 'Retro-Gaming-Screensavers-*-windows-x64-setup.exe' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    if ($Candidates.Count -eq 0) {
        throw 'Download the Windows setup EXE from https://github.com/dt23188/Retro-Gaming-Screensavers/releases or build it with packaging/windows/build-installer.ps1. A source clone does not contain runtime binaries.'
    }
    $InstallerPath = $Candidates[0].FullName
}
$InstallerPath = (Resolve-Path -LiteralPath $InstallerPath).Path
$ChecksumPath = "$InstallerPath.sha256"
if (-not (Test-Path -LiteralPath $ChecksumPath)) { throw "Missing installer checksum: $ChecksumPath" }
$Expected = ((Get-Content -LiteralPath $ChecksumPath -Raw).Trim() -split '\s+')[0]
if ((Get-FileHash -LiteralPath $InstallerPath -Algorithm SHA256).Hash -ine $Expected) { throw 'Installer checksum mismatch' }
$Arguments = @('/NORESTART')
if ($Silent) { $Arguments += @('/VERYSILENT', '/SUPPRESSMSGBOXES') }
$Process = Start-Process -FilePath $InstallerPath -ArgumentList $Arguments -PassThru
$Process.WaitForExit()
if ($Process.ExitCode -ne 0) { throw "Installer failed with exit code $($Process.ExitCode)" }
