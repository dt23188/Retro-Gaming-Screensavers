# Omarchy screensaver rotation

`retro-screensaver` dispatches the installed screensavers and persists a
Classic Snake → Asteroids → Pong rotation between activations. It respects
Omarchy's disabled/locked state and prevents concurrent launches.

It expects the existing `~/.local/bin/omarchy-launch-snake-screensaver` and the
collection's installed `retro-asteroids-screensaver` and
`retro-pong-screensaver` launchers. Install `retro-screensaver` and `retro-screensaver-session.py`
into `~/.local/bin`, then run:

```sh
retro-screensaver select rotation
```

The taskbar button should explicitly call the rotation, independently of any
single-game selection made elsewhere:

```qml
Quickshell.execDetached([Quickshell.env("HOME") + "/.local/bin/retro-screensaver", "rotation", "force"])
```

Use `retro-screensaver run` for idle activation. After modifying a cloned
indicator plugin, reload it with `omarchy-shell shell rescanPlugins`.

The session helper saves the pointer's position relative to its monitor before
launching, waits for all screensaver windows to close, then restores that
position. This covers the taskbar rotation and idle activation, including
Classic Snake's asynchronous multi-monitor launcher. It preserves the relative
position if the monitor moves or changes scale, skips restoration if that
monitor disconnects or the session locks, and leaves global cursor settings
unchanged.
