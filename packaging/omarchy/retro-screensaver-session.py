#!/usr/bin/env python3
"""Keep the pre-screensaver pointer position across Hyprland focus changes."""
import json
import signal
import subprocess
import sys
import time


def query(*args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=3)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def hypr_json(subject):
    try:
        return json.loads(query('hyprctl', '-j', subject) or 'null')
    except ValueError:
        return None


def dimensions(monitor):
    width, height = monitor['width'], monitor['height']
    if monitor.get('transform', 0) % 2:
        width, height = height, width
    return width / monitor.get('scale', 1), height / monitor.get('scale', 1)


def capture_pointer():
    pointer, monitors = hypr_json('cursorpos'), hypr_json('monitors')
    if not isinstance(pointer, dict) or not isinstance(monitors, list):
        return None
    for monitor in monitors:
        width, height = dimensions(monitor)
        x, y = pointer['x'] - monitor['x'], pointer['y'] - monitor['y']
        if 0 <= x < width and 0 <= y < height:
            return monitor['name'], x / width, y / height
    return None


def restore_pointer(saved):
    # Don't move focus on the lock screen or onto a disconnected output.
    if saved is None or query('omarchy-shell', 'lock', 'isLocked') != 'false':
        return
    monitors = hypr_json('monitors')
    if not isinstance(monitors, list):
        return
    name, relative_x, relative_y = saved
    for monitor in monitors:
        if monitor['name'] != name or monitor.get('disabled', False):
            continue
        width, height = dimensions(monitor)
        x = round(monitor['x'] + min(width - 1, relative_x * width))
        y = round(monitor['y'] + min(height - 1, relative_y * height))
        result = query('hyprctl', 'dispatch', f'hl.dsp.cursor.move({{ x = {x}, y = {y} }})')
        if result is None or 'error' in result.lower() or 'invalid' in result.lower():
            query('hyprctl', 'dispatch', 'movecursor', str(x), str(y))
        return


def screensaver_windows():
    clients = hypr_json('clients')
    if not isinstance(clients, list):
        return None
    return {client['address'] for client in clients
            if client.get('class') == 'org.omarchy.screensaver'
            or client.get('initialClass') == 'org.omarchy.screensaver'}


def run(command):
    existing = screensaver_windows()
    saved = capture_pointer() if existing == set() else None
    child = subprocess.Popen(command)
    previous_handlers = {}

    def forward_signal(signum, _frame):
        if child.poll() is None:
            child.send_signal(signum)

    for signum in (signal.SIGTERM, signal.SIGINT):
        previous_handlers[signum] = signal.signal(signum, forward_signal)
    try:
        status = child.wait()
        if saved is not None:
            # Qt owns its windows until exit, but the Classic Snake/terminal
            # launchers exit as soon as their independently spawned windows map.
            # Wait for every monitor's window, then let close/focus events settle.
            while True:
                windows = screensaver_windows()
                if windows is None:
                    return status
                if not windows:
                    time.sleep(.15)
                    windows = screensaver_windows()
                    if windows is None:
                        return status
                    if not windows:
                        break
                time.sleep(.1)
            restore_pointer(saved)
        return status if status >= 0 else 128 - status
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit('Usage: retro-screensaver-session.py COMMAND [ARG ...]')
    raise SystemExit(run(sys.argv[1:]))
