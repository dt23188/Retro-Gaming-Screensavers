# Asteroids Screensaver

Autonomous endless flight, shaded rocky asteroids, enemy fleets, tactical
missiles/shields/radial blasts, enemy drops and smooth native-resolution warp
travel. Starts in a 15-second warp, then arrives at an asteroid belt.

The camera trails the ship so its screen position shifts with travel direction
and speed, easing back toward center when it slows or reverses. Normal flight
stays within 18% of the shorter screen dimension from center; warp cruise also
drifts instead of holding the ship on the same pixels.

Blaster rounds fire straight along the ship's nose without inheriting sideways
drift. Missiles also launch forward before their homing guidance takes over.
Enemy engines have pulsing exhaust and travelling shock rings. Firing briefly
illuminates each ship's forward hull, and blaster hits create contact sparks
and a short expanding flash, including hits absorbed by player protection.

Enemy fleets steer toward the player, circle at combat range, and predict
asteroid crossings so they can turn away and shoot a path through the rocks.
They also pursue nearby power-ups: shields protect them for eight seconds,
missile pickups provide four homing rounds, and blasts break nearby asteroids
without awarding player points. Warp cores remain available to the player.
Occasional rival ships raid each territory: raiders enter ring territory,
marauders enter raider territory, and ring ships enter marauder territory.
Rival fleets unlock after the second completed warp jump (including the opening
warp). Resident fleets travel in groups of three; rival groups contain two ships.
Wingmates follow their leader in formation, leaving space between ships and
breaking away to dodge asteroids. A surviving wingmate takes over if the leader
is destroyed. Only one group from each faction is active at a time.
Rival groups first arrive 22 seconds into eligible territory, then at 26–36
second intervals when residents are present. Their visits last ten seconds. Both fleets prioritize opposing ships over the player, falling back
to the player when no opposing ship remains. Fleet shots ignore their own
faction, and fleet-on-fleet kills do not award player points.

The player has two hit points per life, with 1.2 seconds of protection after
the first hit.

Fullscreen uses one world across all connected monitors, matching their desktop
positions and logical sizes. The ship, projectiles and enemies can cross screen
seams. On multiple monitors, camera travel expands toward the combined desktop's
outer edges (a 10% inset on each axis), then eases back when motion stops or
reverses. Uncovered corners around unequal-sized displays keep the ship visible.
Each screen renders its own portion at native resolution; simulation advances
once per frame regardless of monitor count. Preview and frame-export modes keep
a single viewport. Changing the monitor layout exits the screensaver; the next
launch picks up the new arrangement.

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

Preview: `retro-asteroids-screensaver --preview` on Linux.
For development install `requirements-portable.txt`, then run
`python3 src/retro_portable.py --preview` (Pong needs its compiled executable).

## License

Original project code is licensed under the [MIT License](LICENSE). Third-party libraries retain their own licenses; see [THIRD-PARTY.md](THIRD-PARTY.md).
