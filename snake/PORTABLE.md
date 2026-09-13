# Installation, bundled libraries, and offline releases

Each game has Ubuntu/general-Linux, macOS, and Windows installers. Installers
prefer a matching bundled native runtime and otherwise build from source.
They preserve existing idle timeout and password preferences. Manual fullscreen
animation is not itself a password lock.

## What is bundled

The collection includes one shared **Linux x86_64 runtime** containing Python,
its required standard-library modules, Qt/PySide6 libraries/plugins, both Python
games, and compiled Pong with raylib. It does not include a complete Python/C++
development installation. No pip, Python installer, CMake or compiler is needed
on compatible target machines. Game sources and dependency notices are included.

**This actual Linux build requires glibc 2.44 or newer**, matching the build
machine. It was tested here, not on Ubuntu. Graphics drivers, a working desktop,
and basic OS libraries remain system dependencies; glibc is not replaced.
The installer checks compatibility before using the payload. Ubuntu 22.04,
24.04 and older-glibc Linux desktops will use source installation online unless
you first create a compatible bundle on their oldest target distribution.

Native runtimes are distributed as platform-specific release downloads.
The Windows x64 release includes an offline setup EXE and shared runtime;
see [Windows installation](../windows/README.md). macOS native builders are included. Building on the corresponding OS
creates packages that then install without downloading Python/Qt/compiler tools.
Build separately for x86_64 and arm64; a native runtime is not interchangeable
between operating systems or CPU architectures.

## Linux installation

Copy the **whole collection**, including `runtimes/`, and run:

```sh
bash snake/install-linux.sh
# Require offline installation; fail clearly if no compatible payload exists:
bash snake/install-linux.sh --offline
```

The command is `~/.local/bin/retro-snake-screensaver`; add `--preview` for a window.
An application-menu entry includes preview and fullscreen actions.
Use `--prefix DIR` and `--bin-dir DIR` for custom locations. `--source` forces a
source installation; `--skip-deps` uses dependencies already provided in the
installation venv and skips apt/pip. For source installation on other distros,
provide Python 3.10â€“3.14, Qt Essentials and relevant graphics/build libraries,
then use `--source --skip-deps`. Online Ubuntu/Debian installs use apt (sudo)
and a private Python environment. The only Python graphics requirement is
`PySide6-Essentials==6.11.2`, avoiding the much larger unused Qt Addons package.
Pong builds the bundled raylib source rather than fetching its source from Git.

GNOME does not load arbitrary third-party animations inside its built-in lock
screen. Launch manually or configure a supported idle command on your desktop.
For Sway/Hyprland with swayidle, for example:

```sh
swayidle -w timeout 600 "$HOME/.local/bin/retro-snake-screensaver"
```

Keep a separate secure screen-lock timeout. No idle/autostart/locker configuration
is changed automatically. This package does not implement an XScreenSaver
embedded-window hack.

## Windows 10/11, x64

**Recommended:** use the [combined Windows setup EXE](../windows/README.md)
to install all three games, make them appear in the Windows screensaver list,
and register an uninstaller. The instructions below describe individual per-user
installation from a release ZIP or source clone.

Double-click `snake/install-windows.cmd`. If `runtimes/windows-x86_64` exists,
the script verifies its checksums and copies a native `.scr` with its runtime.
No Python/winget/Qt/compiler installation is then needed. Use `-Offline` to
require a payload or `-Source` to force a source build. `-Activate` selects the
new screensaver and saves the previous selection; otherwise selection remains
unchanged. Timeout and sign-in preference remain unchanged.

Source fallback uses existing Python 3.10â€“3.14 or winget to install Python 3.13,
then installs **Qt Essentials** and PyInstaller privately. Pong source builds
also require CMake and Visual Studio 2022 Build Tools with the C++ desktop
workload. For example:

```powershell
winget install --id Kitware.CMake --exact
winget install --id Microsoft.VisualStudio.2022.BuildTools --exact --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
```

Installation lives under `%LOCALAPPDATA%\RetroGamingScreensavers\snake`.
Keep the generated `.scr` beside `_internal`; transfer the entire runtime folder,
not just the executable. `/s`, `/c`, and `/p HWND` implement Windows fullscreen,
configuration and settings preview. The combined Windows package is built and smoke-tested on Windows; see
[VALIDATION.md](../VALIDATION.md) for the exact tests and remaining limits.

## macOS 13+, Apple Silicon or Intel

Double-click `snake/install-macos.command`. With a matching native runtime and
prebuilt `.saver`, it copies the runtime, installs the native ScreenSaverView
bundle, patches its worker location and signs it locally. No Homebrew, Python or
compiler downloads are needed in this path. `--offline` requires such a payload;
`--source` forces source installation.

Source fallback requires Homebrew and Apple's Command Line Tools
(`xcode-select --install`), then installs Python 3.13, Qt Essentials and CMake
for Pong. Select `RetroSnake` in System Settings > Screen Saver.

The native bundle is in `~/Library/Screen Savers/RetroSnake.saver`; keep its
runtime under `~/Library/Application Support/RetroGamingScreensavers/snake`.
Build on a Mac for its architecture. These local bundles are not notarized
universal release binaries. Native compilation, preview, worker permissions,
idle activation and sign-in require validation on the target macOS version.

## Creating offline release packages

From the collection root on the target OS, install build-only dependencies:

```sh
python -m pip install PySide6-Essentials==6.11.2 pyinstaller==6.22.3
python packaging/build-runtime.py
python packaging/archive-release.py
```

Use `python3` on Linux/macOS if needed. Pong builds need CMake and the platform's
C++ toolchain. `--pong-binary PATH` accepts an already compiled native Pong.
macOS also compiles native wrappers with the Command Line Tools. The builder
copies dependency licenses and records architecture, Python version, and Linux
glibc compatibility in `runtimes/PLATFORM-ARCH/manifest.json`. Release ZIPs land
in `releases/` and include games, installers, source and matching libraries.

Use the included `.github/workflows/build-runtimes.yml` in a GitHub repository
root to build Ubuntu 22.04, Windows 2022, Apple Silicon macOS and Intel macOS
packages. It is manual (`workflow_dispatch`) and was not run by this session.
Build Linux releases on the oldest supported distribution so they can run on
newer-glibc systems. The included Dockerfile provides an Ubuntu 22.04 build:

```sh
docker build -f packaging/Dockerfile.ubuntu22 -t retro-screensavers-builder .
mkdir -p releases
docker run --rm -v "$PWD/releases:/out" retro-screensavers-builder
```

Container build/run may require Docker permissions. This machine's Docker daemon
requires administrator authentication, so the Ubuntu container build was not run.

## Standalone folders, updates, and uninstall

A game's folder by itself is a source package. For standalone offline transfer,
copy the matching `runtimes/PLATFORM-ARCH` folder into `snake/runtimes/` first, or
transfer the entire collection. Rebuild native runtime releases after changing
game code; rerunning an installer with an old runtime reinstalls that old build.

Select another native screensaver before removal. Linux: remove the game's
per-user installation directory, launcher, desktop entry, and any idle command
you added. macOS: remove its `.saver` and Application Support directory. Windows:
remove its per-user folder after selecting another saver. Packaging does not
change this source device's current rotation, taskbar or screen-lock setup.

## References and dependency licenses

- Qt package split: https://doc.qt.io/qtforpython-6.8/package_details.html
- Python/runtime bundling: https://pyinstaller.org/en/stable/operating-mode.html
- Native builds and glibc: https://pyinstaller.org/en/stable/usage.html
- ScreenSaverView: https://developer.apple.com/documentation/screensaver/screensaverview
- Windows selection: https://learn.microsoft.com/en-us/windows/win32/devnotes/scrnsave-exe

Qt/Python/PyInstaller retain their own licenses; runtime `NOTICES/` includes
upstream license files. Qt source and replacement libraries are available from
https://download.qt.io/official_releases/qt/ and https://code.qt.io/. Pong's
corresponding raylib source and license are under `pong/vendor/raylib`.
