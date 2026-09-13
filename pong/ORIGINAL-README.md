# Neon Pong

A polished local arcade game built with C++17 and raylib. It includes solo play,
local multiplayer, responsive physics, procedural sound, particles, screen shake,
ball trails, scalable rendering, and a complete match flow. No external art or
audio assets are required.

## Build

On this machine, raylib 5.0 source is available in `.deps/raylib`.
Build with `make -j4` and launch with `./pong` (or `make run`).
The compiled executable is `build/pong`; `pong` is a shortcut to it.
This local build uses GNU Make and g++ without requiring CMake.

You need CMake, a C++17 compiler, Git, and raylib's platform dependencies. CMake
uses an installed raylib 5.x package when available; otherwise it downloads
raylib 5.0 while configuring.

```sh
cmake -S . -B build
cmake --build build --config Release
./build/pong
```

On Windows with a multi-config generator, run `build/Release/pong.exe`.

## Controls

| Action | Control |
|---|---|
| Start solo | `1` or `Enter` |
| Start local versus | `2` |
| Player one | `W` / `S` |
| Player two | `Up` / `Down` |
| Serve early | `Space` |
| Pause | `P` or `Escape` |
| Restart match | `R` |
| Toggle sound | `M` |

Matches are first to seven. The window is resizable and the arena maintains its
16:9 aspect ratio.

## AI vs AI and screensaver

Press **3** on the title screen to watch AI vs AI, or run `./pong --ai-vs-ai`.
AI matches serve automatically and start a new match three seconds after a win.
The background and arena are black.

`./pong --preview --duration 20` previews the silent screensaver in a window.
`./pong --screensaver` runs fullscreen on one output; `--monitor n` selects it.
Any key, mouse button, wheel, or mouse movement dismisses fullscreen mode.
Mouse movement has a one-second startup grace period.

The installed `pong-screensaver` launcher runs a match on each XWayland output
and closes all matches when one is dismissed. Launch immediately with
`omarchy-launch-pong-screensaver force`. Pong is selected for the existing idle
timer and screensaver bar button. Previous plugin files are backed up as
`*.bak.before-pong`; idle and lock deadlines keep their existing settings.

After rebuilding, update the installed binary with:

```sh
install -m755 build/pong ~/.local/share/omarchy-pong/pong
```

Installation scripts are in `screensaver/omarchy/`.

## Desktop launchers and selection

Double-click `Pong Screensaver.desktop` or run `./launch-screensaver.sh`.
Preview options can be passed to the script, such as `--preview --duration 20`.

The application launcher lists Pong Screensaver, Pac-Man Screensaver, and Snake
Screensaver. The bar screensaver button opens the Screensavers menu, also
available through `omarchy menu summon screensavers`. Choose a default there
for the idle timer, or launch any of the three immediately.

CLI: `dt-screensaver list`, `dt-screensaver current`,
`dt-screensaver select snake`, or `dt-screensaver launch force`.

## Increasing difficulty

In all three modes, every 15 seconds of live ball play adds 48 pixels/second
to ball speed (10% of the initial serve speed). The increase preserves the
ball's direction, carries across points, and also raises the paddle-hit speed
limit. Pauses and serve countdowns do not advance the timer. A new match
resets difficulty. This applies to screensaver matches too.

The ball renders as a flickering fireball with a white-hot core, orange flames,
a glowing fire trail that follows bounces, and fading embers in every mode.

## Responsive playfield and AI display

The arena fills the whole window without letterboxing or an inset border.
Paddles, ball positions, and trails adapt when the window changes shape; paddle
height and movement scale with the playfield height. Landscape, ultrawide,
portrait, and high-resolution screens use the same playable physics. Press
F11 to toggle fullscreen during normal play.

AI vs AI (including the screensaver) shows only paddles, fireball, and effects
during rallies. Scores and the next-serve countdown appear for two seconds
between points; match results appear for three seconds before the rematch.
Solo and local versus retain scores and controls during play.

## Alternating screensavers

The Screensavers menu lists AI Pong (fireball), Pac-Man, Snake, and
Snake ↔ AI Pong rotation. The system currently uses the rotation: each
activation alternates Snake then Pong, with its next choice saved across
reboots. Manual launches of an individual screensaver do not advance it.
`dt-screensaver select snake-pong` selects it and starts the sequence with Snake.
Screensaver activations ignored because a saver is already running or disabled
do not advance the sequence.

Paddle hits trigger a strong, fast camera shake and brief horizontal paddle
recoil. Scoring causes a larger, longer shake and wobbles both paddles. Effects
decay smoothly and move only the rendering; collision geometry stays stable.

Wall bounces also trigger a short camera shake. Paddle recoil is a subtler
5-unit horizontal wobble; paddle-hit and scoring shake retain their strength.

## Idle and secure lock animation

After 150 seconds idle, the selected Snake/Pong rotation starts. At the existing
300-second lock deadline, a secure Quickshell lock surface displays the same
kind of animation instead of Pac-Man. The password field stays hidden until
keyboard or mouse input wakes it, and hides again after five seconds without
input. Authentication and the lock deadline retain their existing behavior.

Pong supports `--lock-frames output.png --width px --height px` for offscreen
frames with fireball, impact shake, and Blue/Pink score overlays. Lock workers
render at up to 1280 pixels on the long edge and scale to each display.
Animation game state starts fresh when transitioning into the lock surface.
