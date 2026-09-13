# Retro Gaming Screensavers 1.1.0 — Windows offline installer

One Windows 10/11 x64 setup program installs **Asteroids, Pong and Snake**, a shared
Python/Qt Essentials runtime, native `.scr` launchers in Windows' screensaver list,
Start menu previews and an Installed apps uninstaller. Destination machines do
not need Python, pip, CMake, a compiler or internet access.

Pong now advances in real time using small collision steps, uses a fast Windows
bitmap frame handoff, and retains the last complete image when frame replacement
briefly prevents a read. These fixes eliminate the reproduced slow motion and
black frame flashes.

## Downloads

- `Retro-Gaming-Screensavers-1.1.0-windows-x64-setup.exe`: combined offline setup.
- Its adjacent `.exe.sha256`: setup download checksum.
- `retro-gaming-screensavers-windows-x86_64.zip`: all sources, individual installers,
  build recipes, native shared runtime, dependency notices and file checksums.
- `SHA256SUMS`: checksums of the setup EXE and ZIP.

Install setup, then select **Retro Asteroids**, **Retro Pong** or **Retro Snake** in
Windows Screensaver Settings. Setup preserves the existing selection, idle timeout
and sign-in preference. Select another saver (or None) before uninstalling.
See [Windows instructions](https://github.com/dt23188/Retro-Gaming-Screensavers/blob/main/windows/README.md).

Validated on Windows: all three frozen games and registered launchers render;
setup, in-place upgrade, removal, settings preservation and frame handoff tests
pass. Windows x64 only; ARM64 emulation, 32-bit Windows and macOS were not tested
for this release. The installer is not Authenticode-signed. Linux downloads remain
available in earlier releases; Linux runtimes must be built for their target glibc.
