# Native offline release builds

See [PORTABLE.md](../asteroids/PORTABLE.md#creating-offline-release-packages).

`build-runtime.py` builds one runtime for all three games on the current OS.
It bundles the Python interpreter, Qt Essentials libraries/plugins and Pong.
On macOS it also creates native `.saver` bundles. Windows gets three native `.scr` launchers for the shared host.
`archive-release.py` archives source, installers and matching native payloads.
Use `--source-only` to omit runtime libraries.

The Dockerfile builds against Ubuntu 22.04's glibc. The manual GitHub Actions
workflow builds Ubuntu 22.04, Windows, Apple Silicon macOS and Intel macOS.
It expects this collection to be the repository root; no workflow was triggered.
Build and test native releases on the corresponding system before distribution.

## Combined Windows installer

See [Windows build instructions](../windows/README.md#build-from-source-on-windows).
`windows/build-installer.ps1` builds a checksum-verified shared runtime and compiles
`windows/installer.iss` with Inno Setup 6. Output is a versioned setup EXE and
adjacent SHA-256 checksum in `releases/`. The installer includes all three games,
adds System32 launchers, Start menu previews and an Installed apps uninstaller.

`windows/screensaver.cpp` forwards Windows screensaver arguments to the selected
game in the shared host; a job object also closes the host/worker if a launcher
is terminated. The shared host explicitly bundles all dynamically selected game
modules and includes Pong's real-time and complete-frame retention fixes.
