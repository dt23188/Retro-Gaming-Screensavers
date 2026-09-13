# Native offline release builds

See [PORTABLE.md](../asteroids/PORTABLE.md#creating-offline-release-packages).

`build-runtime.py` builds one runtime for all three games on the current OS.
It bundles the Python interpreter, Qt Essentials libraries/plugins and Pong.
On macOS it also creates native `.saver` bundles. Windows gets a native `.scr`.
`archive-release.py` archives source, installers and matching native payloads.
Use `--source-only` to omit runtime libraries.

The Dockerfile builds against Ubuntu 22.04's glibc. The manual GitHub Actions
workflow builds Ubuntu 22.04, Windows, Apple Silicon macOS and Intel macOS.
It expects this collection to be the repository root; no workflow was triggered.
Build and test native releases on the corresponding system before distribution.
