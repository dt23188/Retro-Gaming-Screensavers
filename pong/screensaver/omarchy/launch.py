#!/usr/bin/env python3
"""Run one Pong match per output and dismiss all when one exits."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

binary = Path.home() / '.local/share/omarchy-pong/pong'
args = sys.argv[1:]
if '--preview' in args or '--help' in args or '-h' in args:
    os.execv(str(binary), [str(binary), *args])
count = 1
try:
    result = subprocess.run(['xrandr', '--listmonitors'], check=True, capture_output=True, text=True)
    count = max(1, int(result.stdout.splitlines()[0].split(':')[1]))
except (OSError, ValueError, subprocess.CalledProcessError, IndexError):
    pass
children = []
def stop(*_):
    for child in children:
        if child.poll() is None:
            child.terminate()
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
try:
    for monitor in range(count):
        children.append(subprocess.Popen([str(binary), '--screensaver', '--monitor', str(monitor), *args]))
    while all(child.poll() is None for child in children):
        time.sleep(0.1)
finally:
    stop()
    for child in children:
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
