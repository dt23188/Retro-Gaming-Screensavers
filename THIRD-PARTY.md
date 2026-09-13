# Third-party components

The original project code is MIT-licensed; see [LICENSE](LICENSE). Dependency licenses remain separate and are not replaced by MIT.

- Pong includes raylib source and its zlib license in `pong/vendor/raylib/`.
  Embedded raylib dependencies retain their upstream notices.
- Frozen runtimes include Python, Qt/PySide6 Essentials, and PyInstaller’s bootloader.
  Notices and license texts are provided in `packaging/licenses/`, each game’s
  `THIRD-PARTY.md`, and the runtime’s `NOTICES/` directory.
- Qt libraries are dynamically bundled. Their LGPL/GPL notices, upstream source
  information, and replacement guidance are in `packaging/licenses/Qt/`.

Review the applicable notices before redistributing modified binaries. Runtime
builds copy these notices into the downloadable package.
