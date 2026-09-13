# Retro Gaming Screensavers

Asteroids, Pong and Snake, with Linux, macOS and Windows installers.
Installers prefer bundled native runtimes, then fall back to source installation.

| Game | Linux | macOS | Windows |
| --- | --- | --- | --- |
| [Asteroids](asteroids/README.md) | `asteroids/install-linux.sh` | `asteroids/install-macos.command` | `asteroids/install-windows.cmd` |
| [Pong](pong/README.md) | `pong/install-linux.sh` | `pong/install-macos.command` | `pong/install-windows.cmd` |
| [Snake](snake/README.md) | `snake/install-linux.sh` | `snake/install-macos.command` | `snake/install-windows.cmd` |

**Linux release package:** one shared, tested Linux x86_64 runtime containing the Python
interpreter, needed Python/Qt libraries, all games and compiled Pong/raylib.
It requires **glibc 2.44+**. Compatible machines install offline without fetching
Python, Qt, CMake or a compiler. Graphics drivers and basic OS libraries remain
system dependencies. Source installs use Qt Essentials rather than Qt Addons.

**Other targets:** Windows/macOS offline packages must be built on their OS;
Ubuntu-compatible Linux packages should be built on the oldest target distro.
Native release builders, Ubuntu 22.04 Dockerfile and manual GitHub Actions
workflow are provided in [packaging](packaging/README.md). Those target builds
were not executed on this Linux device. Older Linux systems automatically fall
back to source installation, or `--offline` gives a compatibility error.

Download a complete package from [GitHub Releases](https://github.com/dt23188/Retro-Gaming-Screensavers/releases), extract it, and keep its `runtimes/` folder beside the game folders. A Git clone contains source and installers; bundled runtimes are release downloads. See each game's **PORTABLE.md**
for exact instructions. Windows releases produce `.scr` programs; macOS releases
produce native `.saver` bundles. Existing source projects and installed desktop
screensaver selection/lock behavior are preserved.

See [VALIDATION.md](VALIDATION.md) for actual tests and limitations. Python
runtime bundling and per-OS build requirements follow the
[PyInstaller documentation](https://pyinstaller.org/en/stable/usage.html).

## Games

- **Asteroids:** shaded ships and rocky asteroids, autonomous combat, homing missiles, shields, radial blasts, and 15-second warp travel through an endless procedural world.
- **Pong:** playable modes and Blue vs Pink autonomous matches, fireball trails, impact shake, and increasing ball speed.
- **Snake:** autonomous grid gameplay with a portable fullscreen renderer.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for tests and native builds, and [THIRD-PARTY.md](THIRD-PARTY.md) for dependency notices. Manual fullscreen launchers display animation; password protection belongs to the operating system’s lock/screen-saver integration.

## License

A license for the original project code has not been selected yet; no reuse license is granted at this time. Third-party components retain their upstream licenses and notices.
