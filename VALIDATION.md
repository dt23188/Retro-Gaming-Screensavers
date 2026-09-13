# Actual validation on this Linux device

- Built one shared frozen runtime with Python 3.14.7, Qt 6.11.2 and PyInstaller
  6.22.3; includes compiled Pong/raylib. Linux x86_64, glibc 2.44+.
- Ran Asteroids, Pong and Snake frame workers from that runtime successfully.
- Installed all three games offline into temporary paths containing spaces.
  No apt, pip, Python setup, winget or build tool downloads were used.
- Ran all three installed launchers successfully.
- Verified payload checksums, shell syntax, Python compilation and release ZIP.
- Existing portable rendering and Snake portability tests pass on this device.

Ubuntu apt bootstrap, Ubuntu 22.04 Docker/CI build, Windows native build/install,
MSVC compilation, macOS native .saver compilation/install, and those systems'
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
