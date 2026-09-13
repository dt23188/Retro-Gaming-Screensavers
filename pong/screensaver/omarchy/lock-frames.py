#!/usr/bin/python3
"""Select the current idle animation for a secure Quickshell lock surface."""
import argparse
import os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('output')
parser.add_argument('--width', type=int, default=1280)
parser.add_argument('--height', type=int, default=720)
parser.add_argument('--mode', choices=['pong', 'snake', 'pacman', 'asteroids'])
parser.add_argument('--duration', type=float, default=0)
args = parser.parse_args()
home = Path.home()
config = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')) / 'omarchy'
state = Path(os.environ.get('XDG_STATE_HOME', home / '.local/state')) / 'omarchy'
def read(path, fallback):
    try: return path.read_text().strip()
    except OSError: return fallback
choice = args.mode or read(config / 'screensaver-choice', 'snake-pong')
if choice in ('snake-pong', 'snake-pong-asteroids'):
    allowed = ('pong', 'snake', 'asteroids') if choice == 'snake-pong-asteroids' else ('pong', 'snake')
    choice = read(state / 'screensaver-active', 'snake')
    if choice not in allowed: choice = 'snake'
if choice not in ('pong', 'snake', 'pacman', 'asteroids'): choice = 'snake'
if choice == 'asteroids':
    command = ['/usr/bin/python3', str(home / '.local/share/omarchy-asteroids/app.py'), '--lock-frames', args.output]
elif choice == 'snake':
    command = ['/usr/bin/python3', str(home / '.local/share/omarchy-snake/lock-frames.py'), args.output]
else:
    binary = home / ('.local/share/omarchy-pong/pong' if choice == 'pong' else '.local/share/omarchy-pacman/pacman-screensaver')
    command = [str(binary), '--lock-frames', args.output]
command += ['--width', str(args.width), '--height', str(args.height)]
if args.duration: command += ['--duration', str(args.duration)]
os.execv(command[0], command)
