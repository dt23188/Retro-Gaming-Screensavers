param(
    [string]$Python = 'python',
    [string]$PongBinary,
    [string]$Iscc,
    [string]$Version,
    [switch]$SkipRuntimeBuild
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Payload = "$Root\runtimes\windows-x86_64"
if (-not $Version) { $Version = (Get-Content "$PSScriptRoot\release-version.txt" -Raw).Trim() }
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid release version' }
function Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed with exit code $LASTEXITCODE" }
}
if (-not $SkipRuntimeBuild) {
    $BuildArgs = @("$Root\packaging\build-runtime.py")
    if ($PongBinary) { $BuildArgs += @('--pong-binary', $PongBinary) }
    Checked $Python $BuildArgs
}
if (-not (Test-Path "$Payload\manifest.json")) { throw 'Build the Windows x64 runtime first.' }
$Meta = Get-Content "$Payload\manifest.json" -Raw | ConvertFrom-Json
if ($Meta.os -ne 'windows' -or $Meta.architecture -ne 'x86_64') { throw 'This installer needs a Windows x64 payload.' }
foreach ($Line in Get-Content "$Payload\SHA256SUMS") {
    $Hash = $Line.Substring(0,64)
    $Relative = $Line.Substring(66)
    if ((Get-FileHash -LiteralPath (Join-Path $Payload $Relative)).Hash -ine $Hash) { throw "Payload checksum failed: $Relative" }
}
if (-not $Iscc) {
    $Found = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($Found) { $Iscc = $Found.Source }
    else {
        foreach ($Candidate in @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")) {
            if (Test-Path -LiteralPath $Candidate) { $Iscc = $Candidate; break }
        }
    }
}
if (-not $Iscc) { throw 'Install Inno Setup 6: winget install --id JRSoftware.InnoSetup --exact' }
$Output = "$Root\releases"
New-Item -ItemType Directory -Force $Output | Out-Null
Checked $Iscc @("/DPayloadDir=$Payload", "/DOutputDir=$Output", "/DAppVersion=$Version", "$PSScriptRoot\installer.iss")
$Setup = Join-Path $Output "Retro-Gaming-Screensavers-$Version-windows-x64-setup.exe"
$Hash = (Get-FileHash -LiteralPath $Setup).Hash.ToLowerInvariant()
"$Hash  $([IO.Path]::GetFileName($Setup))" | Set-Content -LiteralPath "$Setup.sha256" -Encoding ascii
Write-Host "Installer ready: $Setup"
