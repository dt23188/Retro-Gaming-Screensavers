# Snake Screensaver

Autonomous competing snakes, glowing food and smooth movement. The common
screensaver frontend runs one simulation per monitor. The legacy Snake Qt
frontend (`src/portable.py`) also retains connected-monitor travel/settings.

| System | Installer |
| --- | --- |
| Linux/Ubuntu | `bash install-linux.sh` |
| macOS | `install-macos.command` |
| Windows | `install-windows.cmd` |

Installers prefer a bundled native runtime: no Python/Qt/compiler downloads
are needed when a compatible payload is present. Otherwise they build from
source using Qt Essentials. Add `--offline` on Linux/macOS or `-Offline` on
Windows to require a bundled payload.

**Included now:** a tested Linux x86_64 runtime requiring glibc 2.44+.
**Build on target OS:** Ubuntu-compatible older-glibc, Windows and macOS offline
releases. Windows/macOS binaries are not contained in this Linux-built package.

See [PORTABLE.md](PORTABLE.md) for prerequisites, native builds, selection,
idle activation, standalone transfer and removal. Copy the whole collection
including `runtimes/` for offline installation.

Preview: `retro-snake-screensaver --preview` on Linux.
For development install `requirements-portable.txt`, then run
`python3 src/retro_portable.py --preview` (Pong needs its compiled executable).
