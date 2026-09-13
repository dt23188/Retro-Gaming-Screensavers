param([string]$InstallDir, [switch]$Activate, [switch]$Offline, [switch]$Source)
$ErrorActionPreference='Stop'
$ProjectDir=$PSScriptRoot
$Config=Get-Content "$ProjectDir\game.json" | ConvertFrom-Json
$Game=$Config.game
$Name=$Config.name
if (-not $InstallDir) {$InstallDir="$env:LOCALAPPDATA\RetroGamingScreensavers\$Game"}
function Checked([string]$Program,[string[]]$Arguments) {
 & $Program @Arguments
 if ($LASTEXITCODE -ne 0) {throw "$Program failed with exit code $LASTEXITCODE"}
}
$Arch=if ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture -eq 'Arm64') {'arm64'} else {'x86_64'}
$Payload=$null
foreach ($Path in @("$ProjectDir\runtimes\windows-$Arch","$ProjectDir\..\runtimes\windows-$Arch")) {
 if (Test-Path "$Path\manifest.json") {$Payload=$Path;break}
}
if ($Payload -and -not $Source) {
 foreach ($Line in Get-Content "$Payload\SHA256SUMS") {
  $Hash=$Line.Substring(0,64);$File=$Line.Substring(66)
  if ((Get-FileHash (Join-Path $Payload $File) -Algorithm SHA256).Hash.ToLower() -ne $Hash) {throw "Runtime checksum failed: $File"}
 }
 $Runtime="$InstallDir\runtime"
 New-Item -ItemType Directory -Force $Runtime | Out-Null
 Copy-Item -Recurse -Force "$Payload\RetroScreensaver\*" $Runtime
 $Scr="$Runtime\$Name.scr"
 $Native="$Runtime\Retro Asteroids.scr"
 if (Test-Path $Native) {Copy-Item -Force $Native $Scr} else {Copy-Item -Force "$Runtime\RetroScreensaver.exe" $Scr}
 # The copied launcher reads game.json beside itself, without Python installed.
 Copy-Item -Force "$ProjectDir\game.json" "$Runtime\game.json"
} else {
 if ($Offline) {throw 'No matching bundled Windows runtime. Build the Windows release first; see PORTABLE.md.'}
$Python=$null
if (Get-Command py.exe -ErrorAction SilentlyContinue) {
 $Python=& py.exe -3 -c 'import sys;print(sys.executable)'
 if ($LASTEXITCODE -ne 0) {$Python=$null}
}
if (-not $Python) {
 $Python="$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
 if (-not (Test-Path $Python)) {
  if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {throw 'Install Python 3.13 from python.org, then run again.'}
  Checked winget.exe @('install','--id','Python.Python.3.13','--exact','--scope','user','--accept-package-agreements','--accept-source-agreements')
  if (-not (Test-Path $Python)) {throw 'Reopen the installer after Python installation.'}
 }
}
Checked $Python @('-c','import sys;assert (3,10)<=sys.version_info[:2]<(3,15), "Python 3.10-3.14 required"')
New-Item -ItemType Directory -Force $InstallDir | Out-Null
Checked $Python @('-m','venv',"$InstallDir\venv")
$VenvPython="$InstallDir\venv\Scripts\python.exe"
Checked $VenvPython @('-m','pip','install','-r',"$ProjectDir\requirements-portable.txt",'pyinstaller>=6.12,<7')
Copy-Item -Recurse -Force "$ProjectDir\src" $InstallDir
Copy-Item -Force "$ProjectDir\game.json" $InstallDir
$Extra=@()
if ($Game -eq 'pong') {
 $Cmake=(Get-Command cmake.exe -ErrorAction SilentlyContinue).Source
 if (-not $Cmake) {$Cmake="$env:ProgramFiles\CMake\bin\cmake.exe"}
 if (-not (Test-Path $Cmake)) {throw 'Install CMake and Visual Studio 2022 Build Tools with Desktop development with C++, then run again. See PORTABLE.md.'}
 Checked $Cmake @('-S',$ProjectDir,'-B',"$InstallDir\build-pong",'-DBUILD_SHARED_LIBS=OFF')
 Checked $Cmake @('--build',"$InstallDir\build-pong",'--config','Release','--parallel','2')
 $Pong="$InstallDir\build-pong\Release\pong.exe"
 if (-not (Test-Path $Pong)) {$Pong="$InstallDir\build-pong\pong.exe"}
 if (-not (Test-Path $Pong)) {throw 'Pong build did not produce pong.exe.'}
 $Extra=@('--add-binary',"$Pong;.")
}
$BuildArgs=@('-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed','--name',$Name,'--distpath',"$InstallDir\dist",'--workpath',"$InstallDir\build-host",'--specpath',$InstallDir,'--add-data',"$InstallDir\game.json;.")
$BuildArgs+=$Extra
$BuildArgs+="$InstallDir\src\retro_portable.py"
Checked $VenvPython $BuildArgs
$Scr="$InstallDir\dist\$Name\$Name.scr"
Copy-Item -Force "$InstallDir\dist\$Name\$Name.exe" $Scr
}
if ($Activate) {
 $Key='HKCU:\Control Panel\Desktop'
 if (-not (Test-Path "$InstallDir\previous-screensaver.json")) {
  $Before=Get-ItemProperty $Key
  @{'SCRNSAVE.EXE'=$Before.'SCRNSAVE.EXE';ScreenSaveActive=$Before.ScreenSaveActive} | ConvertTo-Json | Set-Content "$InstallDir\previous-screensaver.json"
 }
 Set-ItemProperty $Key -Name 'SCRNSAVE.EXE' -Value $Scr
 Set-ItemProperty $Key -Name 'ScreenSaveActive' -Value '1'
} else {
 Write-Host "To select this screensaver: right-click '$Scr' and choose Install, or rerun with -Activate."
}
Write-Host "Installed: $Scr (keep its _internal folder beside it)."
Start-Process control.exe -ArgumentList 'desk.cpl,,@screensaver'
