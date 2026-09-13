# Validation

## Windows x64 — September 12, 2026

- Built the shared runtime on Windows 11 x64 with Python 3.13.15, Qt Essentials
  6.11.2, PyInstaller 6.22.3, MinGW and Inno Setup 6.7.3.
- All three frozen games render without the development toolchain on PATH.
- Tested offline setup and in-place upgrade into a temporary path with spaces.
- Tested all three System32 launchers against the registered shared runtime.
- Tested uninstall: runtime, launchers and product registry entries are removed.
- Confirmed screensaver selection, active state, idle timeout and sign-in settings
  remain unchanged. Restored previous standalone screen savers after testing.
- Pong frame worker improved from about 7 FPS to about 60 FPS in five-second runs.
- Frame retention regression tests cover missing, corrupt and replacement frames.
  A live six-second test recorded 663 paints with zero black flashes.
- Seven frame handoff/portable renderer tests pass.

The release workflow also builds with MSVC and tests the installer lifecycle on
Windows Server 2022 before publishing. Windows 10, ARM64 emulation, 32-bit Windows,
password-protected idle activation and macOS integration were not tested here.

## Earlier Linux validation

- Built one shared frozen runtime with Python 3.14.7, Qt 6.11.2 and PyInstaller
  6.22.3; includes compiled Pong/raylib. Linux x86_64, glibc 2.44+.
- Ran Asteroids, Pong and Snake frame workers from that runtime successfully.
- Installed all three games offline into temporary paths containing spaces.
  No apt, pip, Python setup, winget or build tool downloads were used.
- Ran all three installed launchers successfully.
- Verified payload checksums, shell syntax, Python compilation and release ZIP.
- Existing portable rendering and Snake portability tests pass on this device.

Ubuntu apt bootstrap, Ubuntu 22.04 Docker/CI build, Windows native build/install and MSVC compilation (now covered by the Windows
section/release workflow), macOS native .saver compilation/install, and those systems'
idle/sign-in behavior have not been validated here. Docker requires administrator
credentials on this device. Native build recipes are supplied; this archive
contains no prebuilt Windows/macOS runtime. Older glibc Linux targets use source
fallback or need an appropriately built native release.

The installed Omarchy rotation, taskbar widget, idle and lock configuration were
not modified. Source-project portable installer files are synchronized with the
collection; gameplay files remain unchanged by installer work.

Repository preparation: all 33 Asteroids tests, four portable rendering tests,
and three Snake portability tests passed. Source Git files exclude generated
runtimes and local desktop shortcuts. Release archives contain their own exact
file checksum manifests.
