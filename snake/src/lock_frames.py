#!/usr/bin/python3
"""Render Snake frames for the secure Quickshell lock surface."""
import argparse
import os
import sys
import time
from pathlib import Path
import cairo
from graphics import grid, render_arena
from snake import Arena

parser = argparse.ArgumentParser()
parser.add_argument('output')
parser.add_argument('--width', type=int, default=1280)
parser.add_argument('--height', type=int, default=720)
parser.add_argument('--duration', type=float, default=0)
args = parser.parse_args()
if not (100 <= args.width <= 16384 and 100 <= args.height <= 16384) or args.duration < 0:
    parser.error('invalid dimensions or duration')
output = Path(args.output)
scale = min(1, 1280 / max(args.width, args.height))
width, height = max(1, round(args.width * scale)), max(1, round(args.height * scale))
started = last_step = time.monotonic()
arena = Arena(*grid(width, height), elapsed=0)
previous = {}
sparks = []
surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
context = cairo.Context(surface)
while args.duration <= 0 or time.monotonic() - started < args.duration:
    now = time.monotonic()
    if now-last_step >= 1/12:
        previous = {identity: (actor, list(actor.body))
                    for identity, actor in arena.snakes.items()}
        sparks.extend((*food, now) for food in arena.step(now-started))
        last_step = now
    sparks = [spark for spark in sparks if now-spark[2] < .6]
    render_arena(context, arena, previous, min(1, (now-last_step)*12),
                 width, height, now, sparks, elapsed=now-started)
    temporary = output.with_suffix('.tmp')
    surface.write_to_png(str(temporary))
    os.replace(temporary, output)
    print('frame', flush=True)
    time.sleep(max(0, 1/24-(time.monotonic()-now)))
