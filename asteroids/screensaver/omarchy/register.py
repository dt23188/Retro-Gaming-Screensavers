"""Register Infinite Asteroids in this device's existing screensaver menu."""

from pathlib import Path
import json
import re

home = Path.home()


def backup(path):
    saved = path.with_name(path.name + ".bak.before-asteroids")
    if not saved.exists():
        saved.write_bytes(path.read_bytes())


registry = home / ".local/bin/dt-screensaver"
if registry.exists():
    backup(registry)
    text = registry.read_text()
    if "snake-pong|asteroids" not in text:
        text = text.replace(
            "pong|pacman|snake|snake-pong", "pong|pacman|snake|snake-pong|asteroids"
        )
        text = text.replace(
            "pong pacman snake snake-pong;", "pong pacman snake snake-pong asteroids;"
        )
    registry.write_text(text)

menu = home / ".config/omarchy/extensions/omarchy-menu.jsonc"
if menu.exists():
    backup(menu)
    original = menu.read_text()
    data = json.loads(re.sub(r",\s*([}\]])", r"\1", re.sub(r"//[^\n]*", "", original)))
    data.setdefault(
        "screensavers",
        {"icon": "󰍹", "label": "Screensavers", "aliases": ["screensaver"]},
    )
    data["screensavers"][
        "description"
    ] = "Asteroids, AI Pong, Pac-Man, Snake, and Snake / AI Pong rotation"
    data["screensavers.default.asteroids"] = {
        "label": "Infinite Asteroids",
        "description": "Autonomous ship, splitting asteroids, and an endless following camera",
        "action": "~/.local/bin/dt-screensaver select asteroids",
        "checked": 'test "$(~/.local/bin/dt-screensaver current)" = asteroids',
    }
    data["screensavers.start.asteroids"] = {
        "label": "Infinite Asteroids",
        "action": "~/.local/bin/dt-screensaver asteroids force",
    }
    # Keep the introductory JSONC comments when editing the existing menu.
    start = original.find('  "screensavers"')
    prefix = original[:start] if start >= 0 else "{\n"
    menu.write_text(prefix + json.dumps(data, ensure_ascii=False, indent=2)[2:])

coordinator = home / ".local/share/omarchy-pong/lock-frames.py"
if coordinator.exists():
    backup(coordinator)
    text = coordinator.read_text()
    text = text.replace(
        "choices=['pong', 'snake', 'pacman']",
        "choices=['pong', 'snake', 'pacman', 'asteroids']",
    )
    text = text.replace(
        "if choice not in ('pong', 'snake', 'pacman'):",
        "if choice not in ('pong', 'snake', 'pacman', 'asteroids'):",
    )
    if "if choice == 'asteroids':" not in text:
        text = text.replace(
            "if choice == 'snake':\n",
            "if choice == 'asteroids':\n    command = ['/usr/bin/python3', str(home / '.local/share/omarchy-asteroids/app.py'), '--lock-frames', args.output]\nelif choice == 'snake':\n",
        )
    coordinator.write_text(text)
    project = home / "Projects/Pong/screensaver/omarchy/lock-frames.py"
    if project.exists():
        project.write_text(text)
