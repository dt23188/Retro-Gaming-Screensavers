# Omarchy Snake

Native Python / GTK 3 / Cairo screensaver. Antialiased rounded geometry,
interpolated movement, distinct colored snakes with eyes and highlights, glowing
amber food, and short pickup particles. Pure black background, no grid or
permanent HUD. Uses libraries already installed on this machine.

## Launch

```sh
~/.local/bin/omarchy-launch-snake-screensaver force
```

The launcher opens a native fullscreen window on each active monitor. It uses
Omarchy's `org.omarchy.screensaver` identity, so the existing idle service and
lock command recognize and close it. Any key, mouse button, scroll, mouse
movement, focus leaving the screensaver, or a termination signal exits.
Exiting one fullscreen instance closes them all. Cursor hiding is local to the
window, so it does not change the global compositor cursor setting.

### Shared game across displays

Run one shared competition across the current display arrangement:

```sh
~/.local/bin/omarchy-launch-snake-screensaver force --span-monitors
```

To use spanning for automatic idle launches too, set `"span_monitors": true`
in `~/.config/omarchy/snake.json`. The default is `false` (a separate game per
display). A launch with `--independent-monitors` overrides that setting for
that run. The launcher checks this setting each time it starts.

Spanning uses the active monitors' logical positions and dimensions reported
by GDK, including the system's scaling and rotation. A single process advances
one simulation and draws a fullscreen viewport on each display. Snakes can
straddle displays and chase the same food across them. Only the overlapping
portion of touching edges allows passage; exposed edges, gaps and corner-only
contacts are walls. Negative positions, stacked and offset displays are
supported. Mirrored rectangles share one viewport. Disconnected displays
cannot be crossed. Snake and food population limits apply to the whole arena.

Only active displays participate. On a monitor geometry change, connection or
disconnection, the spanning screensaver exits cleanly; the next launch uses the
new layout. It does not change monitor settings or turn on disabled displays.

Preview the entire active layout in one window:

```sh
~/.local/bin/omarchy-snake --preview --span-monitors
```

Windowed preview (closes only itself):

```sh
~/.local/bin/omarchy-snake --preview
~/.local/bin/omarchy-snake --preview --speed 20 --cell-size 24
```

`--cell-size` sets approximate cell spacing in logical pixels (default 28;
12–100 supported). The snake is thinner than the cell, with a tapered tail.
`--speed` sets moves per second (default 14). Display animation is synchronized
with the window frame clock and interpolates between game moves. `--duration 10`
exits after ten seconds; `--seed 42` makes initial food/layout reproducible.

Rendering smooths alternating horizontal/vertical steps into diagonal paths,
including the head's motion, and uses tangent-continuous curves for bends.
The simulation still uses grid cells for food, collisions and display-edge
traversal. Both monitor modes use the same smoothing.

The grid fills the display and adapts to its resolution, scaling and aspect
ratio. A change in grid dimensions rebuilds the arena while preserving elapsed-time
population targets.

## AI and integration

The native screensaver starts with one snake and one food orb. It adds a food
orb every 8 seconds (up to 12), and another snake every 20 seconds (up to 6).
Small grids reduce the caps to leave room to move. Each snake has its own color.
All snakes compete for the same food, using bounded breadth-first searches for
reachable food while avoiding walls and every snake's body. Movement priority
rotates so contested food does not always favor the same snake. Eaten food is
replenished in empty cells; growth is capped to keep the animation moving.
Trapped snakes respawn after 14 stalled moves. New snakes spawn only where a
whole body fits and appear without interpolating across the screen.

Food lasts 30 seconds, fading smoothly over its final 5 seconds (including its
glow and highlight). Expired food is replaced in another empty cell, and its old
cell cannot host food for 30 more seconds. Timing follows elapsed seconds,
independently of movement speed, and is shared across spanning viewports.
On crowded boards, replacement waits for an eligible empty cell.

`snake.py` also retains the legacy single-snake terminal game and its safe
Hamiltonian-cycle AI. No network, external AI service or model is used.

Automatic launch uses `~/.config/omarchy/plugins/rf.idle/Service.qml`. Idle and
lock timers remain 1800 and 3600 seconds. Stay Awake was enabled at installation;
turn it off in Omarchy's indicators for automatic idle activation.

The stock/manual Omarchy screensaver command and previous Matrix customization
remain available. To restore built-in automatic idle behavior:

```sh
omarchy plugin enable omarchy.idle
```

## Source and validation

- `graphics.py`: native renderer, animation, input and window lifecycle.
- `snake.py`: shared game engine and optional legacy terminal renderer.
- `topology.py`: irregular board constructed from exact logical display edges.
- `test_snake.py`: timed population, shared-food competition, long-run collision checks,
  and legacy single-snake tests.
- `test_topology.py`: cross-screen traversal, exposed walls, gaps, stacked and
  offset displays, and irregular-board simulation.
- `test_graphics.py`: pixel comparisons of a snake rendered across a display seam.
- `~/.local/bin/omarchy-snake`: native entry point.
- `~/.local/bin/omarchy-launch-snake-screensaver`: user-owned monitor launcher.
- `backup-path.txt`: original shell/idle config backup location.
- Launcher/entry-point `.bak-terminal` files: previous terminal-based versions.

Engine tests:

```sh
/usr/bin/python3 -m unittest discover -s ~/.local/share/omarchy-snake -p 'test_*.py'
```

Native rendering checked at 1920×1080, 3440×1440 and 2160×3840. Fullscreen
identity, launch on every currently active monitor, and termination cleanup
were checked against the running Hyprland session.

GTK reference: https://docs.gtk.org/gtk3/class.DrawingArea.html

Spanning references:
- https://docs.gtk.org/gdk3/method.Monitor.get_geometry.html
- https://docs.gtk.org/gtk3/method.Window.fullscreen_on_monitor.html
