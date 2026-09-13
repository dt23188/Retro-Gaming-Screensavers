# Pong Screensaver

AI-vs-AI Pong with randomized team colors on black, with fireball trails, paddle/wall screen shake,
a responsive playfield and speed increases every 15 seconds. The C++ game also
retains its three interactive play modes.

Fullscreen defaults to an independent randomized match on each active monitor.
Each screen gets a distinct pair of complementary team colors, randomized on
every launch. Scores, ball movement and effects belong to that screen's match.
Use `retro-pong-screensaver --single-monitor` for the primary screen only, or
`--all-monitors` for all screens. Preview remains a single window. Monitor layout
changes exit the screensaver; relaunch to pick up the new arrangement.
The native game also accepts `--team-hue 0..359` to choose a specific palette.

| System | Installer |
| --- | --- |
| Linux/Ubuntu | `bash install-linux.sh` |
| macOS | `install-macos.command` |
| Windows | [Combined setup EXE](../windows/README.md) or `install-windows.cmd` |

Installers prefer a bundled native runtime: no Python/Qt/compiler downloads
are needed when a compatible payload is present. Otherwise they build from
source using Qt Essentials. Add `--offline` on Linux/macOS or `-Offline` on
Windows to require a bundled payload.

**Release downloads:** Linux x86_64 packages and a Windows 10/11 x64 offline
installer for all three games. See the [Windows README](../windows/README.md).
Build older-glibc Linux and macOS packages on their target operating system.

See [PORTABLE.md](PORTABLE.md) for prerequisites, native builds, selection,
idle activation, standalone transfer and removal. Copy the whole collection
including `runtimes/` for offline installation.

Preview: `retro-pong-screensaver --preview` on Linux.
For development install `requirements-portable.txt`, then run
`python3 src/retro_portable.py --preview` (Pong needs its compiled executable).

## License

Original project code is licensed under the [MIT License](LICENSE). Third-party libraries retain their own licenses; see [THIRD-PARTY.md](THIRD-PARTY.md).
