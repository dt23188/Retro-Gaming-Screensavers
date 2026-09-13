# Retro Gaming Screensavers v0.1.1

Asteroids, Pong, and Snake sources, cross-platform installers, dependency notices,
and native runtime build recipes.

Original project code is now licensed under MIT (copyright 2026 dt23188).
Standalone game folders and the bundled runtime include the license. Third-party
libraries retain their upstream licenses. This is a licensing/package update;
gameplay and executable binaries are unchanged. Offline runtime archives now
retain Python’s required bundled standard-library ZIP.

## Downloads

- `retro-gaming-screensavers-linux-x86_64.zip`: tested bundled runtime for Linux
  x86_64 with **glibc 2.44 or newer**. Extract the entire archive and run a game’s
  `install-linux.sh --offline`. This build is not compatible with older Ubuntu
  releases; use the source package or build the Ubuntu 22.04 recipe instead.
- `retro-gaming-screensavers-source.zip`: all three games and installers, no
  bundled runtime. Source installs fetch the dependencies documented per game.
- `SHA256SUMS`: checksums of the release downloads. Each ZIP also includes a
  checksum manifest for its extracted contents.

Windows and macOS installers/build workflows are supplied, but this
release does not include tested native Windows or macOS runtimes. Their native
screensaver integration needs validation on the target OS.

Fullscreen animation alone does not lock the computer. Configure password
protection using your operating system’s screen-saver/lock settings.
