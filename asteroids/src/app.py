#!/usr/bin/python3
"""Infinite Asteroids screensaver: GTK windows or headless Cairo frames."""

import argparse
import json
import math
import os
from pathlib import Path
import random
import signal
import sys
import time

import cairo
from engine import World
from render import render


def dimensions(width, height):
    scale = min(width, height) / 900
    return width / scale, height / scale


def image(world, width, height):
    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
    render(cairo.Context(surface), world, width, height)
    return surface


def offscreen(args):
    width, height = args.width, args.height
    if args.lock_frames:
        scale = min(1, 1280 / max(width, height))
        width, height = max(1, round(width * scale)), max(1, round(height * scale))
    world = World(args.seed, *dimensions(width, height), start_in_warp=True)
    if args.render:
        for _ in range(round(args.simulate * 120)):
            world.step(1 / 120)
        image(world, width, height).write_to_png(args.render)
        print(
            json.dumps(
                {
                    "score": world.score,
                    "shots_fired": world.shots_fired,
                    "rocks_hit": world.rocks_hit,
                    "deaths": world.deaths,
                    "distance": round(world.total_distance),
                    "parts_collected": world.parts_collected,
                    "warp_jumps": world.warps,
                    "zone_fleet": world.zone_fleet,
                }
            )
        )
        return 0
    output = Path(args.lock_frames)
    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
    context = cairo.Context(surface)
    start = last = time.monotonic()
    while not args.duration or time.monotonic() - start < args.duration:
        now = time.monotonic()
        world.advance(now - last)
        last = now
        render(context, world, width, height)
        temporary = output.with_name(output.name + ".tmp")
        surface.write_to_png(str(temporary))
        os.replace(temporary, output)
        print("frame", flush=True)
        time.sleep(max(0, 1 / 24 - (time.monotonic() - now)))
    return 0


def desktop(args):
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk, Gio, GLib, GLibUnix

    app_id = "org.dt.asteroids.preview" if args.preview else "org.omarchy.screensaver"
    GLib.set_prgname(app_id)

    class Saver(Gtk.Application):
        def __init__(self):
            super().__init__(
                application_id=app_id, flags=Gio.ApplicationFlags.NON_UNIQUE
            )
            self.connect("activate", self.activate)
            self.views = []
            self.started = self.last = time.monotonic()
            self.pointer = None
            self.global_pointer = None
            self.closed = False

        def activate(self, *_):
            display = Gdk.Display.get_default()
            if display is None:
                raise RuntimeError(
                    "No graphical display; use --render for headless output"
                )
            monitors = (
                [None]
                if args.preview
                else [display.get_monitor(i) for i in range(display.get_n_monitors())]
            )
            if not monitors:
                raise RuntimeError("No connected monitors")
            for index, monitor in enumerate(monitors):
                window = Gtk.ApplicationWindow(application=self)
                window.set_title("Infinite Asteroids")
                window.set_default_size(args.width, args.height)
                window.set_decorated(args.preview)
                window.add_events(
                    Gdk.EventMask.KEY_PRESS_MASK
                    | Gdk.EventMask.BUTTON_PRESS_MASK
                    | Gdk.EventMask.POINTER_MOTION_MASK
                    | Gdk.EventMask.SCROLL_MASK
                )
                window.connect("delete-event", lambda *_: self.stop())
                window.connect("key-press-event", self.key)
                if not args.preview:
                    window.connect("button-press-event", lambda *_: self.stop())
                    window.connect("scroll-event", lambda *_: self.stop())
                    window.connect("motion-notify-event", self.motion)
                area = Gtk.DrawingArea()
                world = World(
                    args.seed + index,
                    *dimensions(args.width, args.height),
                    start_in_warp=True
                )
                area.connect("draw", self.draw, world)
                window.add(area)
                if monitor is not None:
                    window.fullscreen_on_monitor(window.get_screen(), index)
                    monitor.connect("notify::geometry", lambda *_: self.stop())
                window.show_all()
                if not args.preview:
                    window.get_window().set_cursor(
                        Gdk.Cursor.new_for_display(display, Gdk.CursorType.BLANK_CURSOR)
                    )
                self.views.append((window, area, world))
            if not args.preview:
                display.connect("monitor-added", lambda *_: self.stop())
                display.connect("monitor-removed", lambda *_: self.stop())
                GLib.timeout_add(350, self.check_activity)
            GLib.timeout_add(16, self.tick)
            for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, sig, self.stop)

        def stop(self):
            if not self.closed:
                self.closed = True
                for window, _, _ in self.views:
                    window.destroy()
                self.quit()
            return False

        def key(self, window, event):
            if not args.preview or event.keyval == Gdk.KEY_Escape:
                self.stop()
            return True

        def motion(self, _, event):
            pointer = (event.x_root, event.y_root)
            if (
                time.monotonic() - self.started > 1
                and self.pointer is not None
                and pointer != self.pointer
            ):
                self.stop()
            self.pointer = pointer
            return True

        def check_activity(self):
            if self.closed:
                return False
            if time.monotonic() - self.started < 2:
                return True
            # Focus switching between our own outputs must not dismiss the saver.
            import subprocess

            try:
                result = subprocess.run(
                    ["hyprctl", "-j", "activewindow"],
                    capture_output=True,
                    text=True,
                    timeout=0.3,
                )
                if (
                    result.returncode == 0
                    and json.loads(result.stdout).get("class") != app_id
                ):
                    return self.stop()
                result = subprocess.run(
                    ["hyprctl", "-j", "cursorpos"],
                    capture_output=True,
                    text=True,
                    timeout=0.3,
                )
                if result.returncode == 0:
                    pointer = result.stdout.strip()
                    if (
                        self.global_pointer is not None
                        and pointer != self.global_pointer
                    ):
                        return self.stop()
                    self.global_pointer = pointer
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
            return True

        def tick(self):
            now = time.monotonic()
            dt = now - self.last
            self.last = now
            if args.duration and now - self.started >= args.duration:
                return self.stop()
            for _, area, world in self.views:
                w, h = area.get_allocated_width(), area.get_allocated_height()
                if min(w, h) > 0:
                    ww, wh = dimensions(w, h)
                    if abs(world.width - ww) > 0.1 or abs(world.height - wh) > 0.1:
                        world.resize(ww, wh)
                world.advance(dt)
                area.queue_draw()
            return not self.closed

        def draw(self, area, cr, world):
            render(cr, world, area.get_allocated_width(), area.get_allocated_height())
            return False

    return Saver().run([])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preview", action="store_true", help="resizable window; Escape closes"
    )
    parser.add_argument(
        "--duration", type=float, default=0, help="exit after this many seconds"
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    output = parser.add_mutually_exclusive_group()
    output.add_argument(
        "--render", metavar="OUTPUT.png", help="write one frame without a display"
    )
    output.add_argument(
        "--lock-frames",
        metavar="OUTPUT.png",
        help="stream frames for a secure lock surface",
    )
    parser.add_argument(
        "--simulate",
        type=float,
        default=8,
        help="seconds of simulation before --render",
    )
    args = parser.parse_args()
    if not (100 <= args.width <= 16384 and 100 <= args.height <= 16384):
        parser.error("dimensions must be 100–16384 pixels")
    if (
        not math.isfinite(args.duration)
        or args.duration < 0
        or not math.isfinite(args.simulate)
        or not 0 <= args.simulate <= 3600
    ):
        parser.error("invalid duration or simulation time")
    if args.seed is None:
        args.seed = random.SystemRandom().randrange(1 << 32)
    try:
        return offscreen(args) if args.render or args.lock_frames else desktop(args)
    except (OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
