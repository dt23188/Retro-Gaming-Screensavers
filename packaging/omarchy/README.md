# Omarchy screensaver rotation

`retro-screensaver` dispatches the installed screensavers and persists a
Classic Snake → Asteroids → Pong rotation between activations. It respects
Omarchy's disabled/locked state and prevents concurrent launches.

It expects the existing `~/.local/bin/omarchy-launch-snake-screensaver` and the
collection's installed `retro-asteroids-screensaver` and
`retro-pong-screensaver` launchers. Install it into `~/.local/bin`, then run:

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
