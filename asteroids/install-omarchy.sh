#!/bin/bash
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
/usr/bin/python3 -c 'import cairo, gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk'
install -d "$HOME/.local/share/omarchy-asteroids" "$HOME/.local/bin" "$HOME/.local/share/applications"
install -m644 "$project_dir/src/engine.py" "$project_dir/src/render.py" "$project_dir/src/app.py" "$HOME/.local/share/omarchy-asteroids/"
install -m755 "$project_dir/screensaver/omarchy/asteroids-screensaver" "$project_dir/screensaver/omarchy/omarchy-launch-asteroids-screensaver" "$HOME/.local/bin/"
install -m644 "$project_dir/Infinite Asteroids Screensaver.desktop" "$HOME/.local/share/applications/asteroids-screensaver.desktop"
/usr/bin/python3 "$project_dir/screensaver/omarchy/register.py"
if command -v omarchy >/dev/null; then omarchy menu refresh; fi
printf '%s\n' 'Installed Infinite Asteroids. Launch: omarchy-launch-asteroids-screensaver force'
