# Development and contributions

Use Python 3.10 or newer and a virtual environment. Install each game’s
`requirements-portable.txt` for the Qt frontend. Asteroids’ original renderer
tests also require `pycairo`; building that package may require Cairo headers.

```sh
python -m pip install -r asteroids/requirements-portable.txt pycairo
QT_QPA_PLATFORM=offscreen make test
python -m unittest discover -s asteroids/tests -v
```

Pong’s native build requires CMake, a C++17 compiler, and the platform graphics
libraries described in `pong/PORTABLE.md`. Raylib source is included.

See `packaging/README.md` for frozen runtime builds. Build on each target OS;
PyInstaller does not cross-compile. The manual GitHub Actions workflow builds
Ubuntu 22.04, Windows x86_64, and macOS Intel/Apple Silicon packages. Test the
installer and OS screensaver integration on a target machine before calling a
package validated. Build artifacts are release downloads, not Git source files.

For bug reports, include OS/version, CPU architecture, game, installer command,
and error output. Pull requests should explain the behavior changed and relevant
validation. Do not include local settings, credentials, or generated runtimes.
