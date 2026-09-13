# Windows 10/11 installation (64-bit)

Download **Retro-Gaming-Screensavers-1.1.0-windows-x64-setup.exe** from
[GitHub Releases](https://github.com/dt23188/Retro-Gaming-Screensavers/releases).
The setup program includes Asteroids, Pong, Snake, Python, Qt Essentials and
compiled Pong/raylib. Installation is offline; Python, pip, CMake and a compiler
are not required on the destination computer.

## Install and select a screensaver

1. Close Screensaver Settings and any running screensaver previews.
2. Double-click the setup EXE and approve Windows' administrator prompt.
3. Finish setup, then open **Screensaver Settings** from the Start menu's
   **Retro Gaming Screensavers** folder.
4. Select **Retro Asteroids**, **Retro Pong** or **Retro Snake** and click Apply.
   Use Preview to try the full-screen animation.

Setup installs one shared runtime under
`C:\Program Files\Retro Gaming Screensavers\runtime` and three small `.scr`
launchers under the Windows System32 folder so Windows lists all three savers.
The installer registers an uninstaller in **Settings > Apps > Installed apps**.
It preserves your screensaver selection, idle timeout and sign-in preference.
The Windows x64 package supports Windows 10/11 x64; ARM64 emulation and 32-bit
Windows have not been tested. This release is not Authenticode-signed.

Pong includes real-time simulation, a fast Windows bitmap frame handoff, and
retention of the last complete frame to prevent black flashes during replacement.

## Verify a download and scripted installation

Download the accompanying `.exe.sha256` file. From the repository/release folder:

```powershell
.\windows\install-windows.ps1 -InstallerPath .\releases\Retro-Gaming-Screensavers-1.1.0-windows-x64-setup.exe
# Verify the same checksum and install without the wizard:
.\windows\install-windows.ps1 -InstallerPath .\releases\Retro-Gaming-Screensavers-1.1.0-windows-x64-setup.exe -Silent
```

Double-clicking the root `install-windows.cmd` finds the most recently built setup
EXE in `releases/` and verifies its adjacent checksum before starting it. An
ordinary Git clone contains source and installer recipes; download a release
or build locally before using this entry point.

The release ZIP also includes `runtimes/windows-x86_64/`, all game sources,
dependency notices, individual game installers and checksum manifests. Keep the
entire extracted folder together. Existing `GAME/install-windows.cmd` scripts
remain available for individual per-user source/offline installation; the combined
setup EXE is the recommended way to make all three savers appear in Windows' list.
Do not move just the shared host EXE: it needs its adjacent `_internal` directory.

## Update and remove

Run a newer setup EXE over the previous installation to update all three games.
Close previews first. Before uninstalling, select another screensaver (or None)
in Screensaver Settings. Then uninstall **Retro Gaming Screensavers** in Settings.
This removes the three setup-installed System32 launchers, shared runtime,
shortcuts and runtime registration. Legacy per-user installations made by the
individual scripts are separate; remove those folders separately if unwanted.

## Build from source on Windows

Use Python 3.10â€“3.14, CMake, a C++17 toolchain, and Inno Setup 6. The recommended
compiler is Visual Studio 2022 Build Tools with the Desktop C++ workload.

```powershell
winget install --id Python.Python.3.13 --exact
winget install --id Kitware.CMake --exact
winget install --id Microsoft.VisualStudio.2022.BuildTools --exact --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
winget install --id JRSoftware.InnoSetup --exact
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install PySide6-Essentials==6.11.2 pyinstaller==6.22.3
.\packaging\windows\build-installer.ps1 -Python .\.venv\Scripts\python.exe
```

The build script compiles Pong and the three native launchers, freezes the shared
host, verifies runtime checksums and compiles setup. Output:

- `runtimes/windows-x86_64/`: shared offline runtime, launchers and notices.
- `releases/Retro-Gaming-Screensavers-1.1.0-windows-x64-setup.exe`.
- The setup EXE's adjacent `.sha256` file.

`-PongBinary PATH` accepts an existing native Pong build. Native launchers still
need CMake and a compiler. MinGW builds are supported with `CMAKE_GENERATOR` set to
`MinGW Makefiles` and the toolchain's `bin` directory on PATH; its runtime DLLs
must be available while packaging. `-SkipRuntimeBuild` packages an already built,
checksum-verified payload. `-Version` changes the setup filename/version.

```powershell
.\.venv\Scripts\python.exe packaging\smoke-runtime.py runtimes\windows-x86_64
.\.venv\Scripts\python.exe packaging\archive-release.py
```

The native build workflow uploads the Windows setup, ZIP and checksums as build
artifacts. The Windows release workflow tests installation, upgrade and removal
and publishes them to GitHub Releases. Update `packaging/windows/release-version.txt`
on `main` to publish a new version, or run the release workflow manually. Existing
release tags/assets are never overwritten. Release binaries belong in GitHub Releases,
while build scripts, installer sources and documentation are tracked in Git.

Build/test results and remaining platform limits are recorded in
[VALIDATION.md](../VALIDATION.md). Dependency licenses are in the installed
`NOTICES` folder and source `THIRD-PARTY.md` files.
