param([Parameter(Mandatory=$true)][string]$InstallerPath, [string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$AppId = '{E8393547-525C-4E32-9489-E806B4ACD478}_is1'
$UninstallKey = "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppId"
$RuntimeKey = 'HKLM:\Software\RetroGamingScreensavers'
if ((Test-Path $UninstallKey) -or (Test-Path $RuntimeKey)) {
    throw 'Run this test on a machine without an existing combined-suite installation.'
}
$TestRoot = Join-Path $env:TEMP ('retro-installer-test-' + [guid]::NewGuid().ToString('N'))
$InstallDir = Join-Path $TestRoot 'Installed Suite With Spaces'
$BackupDir = Join-Path $TestRoot 'backups'
New-Item -ItemType Directory -Force $BackupDir | Out-Null
$Names = @('Retro Asteroids.scr','Retro Pong.scr','Retro Snake.scr')
$Previous = @{}
foreach ($Name in $Names) {
    $SystemFile = Join-Path ([Environment]::SystemDirectory) $Name
    $Previous[$Name] = Test-Path -LiteralPath $SystemFile
    if ($Previous[$Name]) { Copy-Item -LiteralPath $SystemFile -Destination (Join-Path $BackupDir $Name) }
}
$Running = Get-CimInstance Win32_Process | Where-Object { ($Names -contains $_.Name) -or ($_.Name -eq 'pong.exe' -and $_.CommandLine -match 'retro-pong-') }
foreach ($Process in $Running) { Stop-Process -Id $Process.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 500
$BeforeSettings = Get-ItemProperty 'HKCU:\Control Panel\Desktop'
function RunChecked([string]$Program, [string[]]$Arguments) {
    $Start = New-Object Diagnostics.ProcessStartInfo
    $Start.FileName = $Program
    $Start.Arguments = [string]::Join(' ', $Arguments)
    $Start.UseShellExecute = $false
    $Start.CreateNoWindow = $true
    $Process = [Diagnostics.Process]::Start($Start)
    if (-not $Process.WaitForExit(60000)) { Stop-Process -Id $Process.Id -Force; throw "$Program timed out" }
    if ($Process.ExitCode -ne 0) { throw "$Program exited $($Process.ExitCode)" }
}
try {
    for ($Pass=1; $Pass -le 2; $Pass++) {
        RunChecked $InstallerPath @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/DIR=`"$InstallDir`"", "/LOG=`"$TestRoot\install-$Pass.log`"")
        if (-not (Test-Path $UninstallKey)) { throw 'Missing uninstall registration' }
        if ((Get-ItemProperty $RuntimeKey).RuntimePath -ne "$InstallDir\runtime") { throw 'Incorrect runtime registration' }
        Write-Host "Install/upgrade pass $Pass OK"
    }
    & $Python "$Root\packaging\smoke-runtime.py" $InstallDir
    # Installed manifests use release-relative paths; test the installed host explicitly.
    if ($LASTEXITCODE -ne 0) { throw 'Installed runtime smoke test failed' }
    foreach ($Name in $Names) {
        $Game = ($Name -replace '^Retro ','') -replace '\.scr$',''
        $Output = Join-Path $TestRoot ($Game + '.png')
        RunChecked (Join-Path ([Environment]::SystemDirectory) $Name) @('--frames',"`"$Output`"",'--duration','1','--width','640','--height','360')
        if (-not (Test-Path -LiteralPath $Output)) { throw "$Name did not select/render its game" }
        Write-Host "$Name registered launcher OK"
    }
    $AfterSettings = Get-ItemProperty 'HKCU:\Control Panel\Desktop'
    foreach ($Name in @('SCRNSAVE.EXE','ScreenSaveActive','ScreenSaveTimeOut','ScreenSaverIsSecure')) {
        if ($BeforeSettings.$Name -ne $AfterSettings.$Name) { throw "Installer changed $Name" }
    }
    RunChecked "$InstallDir\unins000.exe" @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/LOG=`"$TestRoot\uninstall.log`"")
    if ((Test-Path $UninstallKey) -or (Test-Path $RuntimeKey)) { throw 'Uninstall left suite registration behind' }
    foreach ($Name in $Names) {
        if (Test-Path -LiteralPath (Join-Path ([Environment]::SystemDirectory) $Name)) { throw 'Uninstall left a suite launcher behind' }
    }
    if (Test-Path -LiteralPath "$InstallDir\runtime") { throw 'Uninstall left runtime behind' }
    Write-Host 'Uninstall and settings preservation OK'
} finally {
    if ((Test-Path $UninstallKey) -and (Test-Path -LiteralPath "$InstallDir\unins000.exe")) {
        RunChecked "$InstallDir\unins000.exe" @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
    }
    foreach ($Name in $Names) {
        if ($Previous[$Name]) {
            Copy-Item -LiteralPath (Join-Path $BackupDir $Name) -Destination (Join-Path ([Environment]::SystemDirectory) $Name) -Force
        }
    }
    Write-Host "Previous standalone screensavers restored. Test logs: $TestRoot"
}
