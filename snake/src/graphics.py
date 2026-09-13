#!/usr/bin/python3
"""Native, antialiased GTK/Cairo frontend for the Snake AI engine."""
import argparse
import colorsys
from types import SimpleNamespace
import json
import math
import signal
import subprocess
import time

import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GLib
from snake import Arena, hypr
from topology import Topology
from curves import smooth_centerline, curve_controls
from drawing import render, render_arena


def grid(width, height, cell=28):
    return max(4, round(width / cell)), max(4, round(height / cell / 2) * 2)


class Saver(Gtk.Application):
    def __init__(self, args):
        super().__init__(application_id='org.omarchy.screensaver', flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.args = args
        self.start = time.monotonic()
        self.game = None
        self.previous = {}
        self.last_step = self.start
        self.sparks = []
        self.pointer = None
        self.global_pointer = None
        self.views = []
        self.topology = None
        self.connect('activate', self.activate_window)

    def activate_window(self, _):
        if self.args.span_monitors:
            display = Gdk.Display.get_default()
            rectangles = []
            monitors = []
            for index in range(display.get_n_monitors()):
                monitor = display.get_monitor(index)
                geometry = monitor.get_geometry()
                rectangle = (geometry.x, geometry.y, geometry.width, geometry.height)
                if rectangle not in rectangles:
                    rectangles.append(rectangle)
                    monitors.append((index, rectangle))
                # A changed display layout invalidates the arena and its
                # fullscreen viewports. Exit cleanly; next launch reads it anew.
                monitor.connect('notify::geometry', lambda *_: self.close_all())
            display.connect('monitor-added', lambda *_: self.close_all())
            display.connect('monitor-removed', lambda *_: self.close_all())
            self.topology = Topology(rectangles, self.args.cell_size)
            self.game = Arena(self.topology.width, self.topology.height,
                              seed=self.args.seed, cells=self.topology.cells,
                              elapsed=time.monotonic()-self.start)
            if self.args.preview:
                self.create_view()
            else:
                for index, rectangle in monitors:
                    self.create_view(index, rectangle)
            # A single simulation timer feeds every viewport, regardless of
            # monitor refresh rates. Individual frame clocks only redraw.
            GLib.timeout_add(8, self.tick)
        else:
            self.create_view()
            self.area.add_tick_callback(self.tick)
        if not self.args.preview:
            GLib.timeout_add(300, self.check_focus)
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, sig, self.close_all)

    def create_view(self, monitor_index=None, rectangle=None):
        window = Gtk.ApplicationWindow(application=self)
        window.set_title('Snake AI')
        window.set_default_size(1100, 700)
        window.set_decorated(self.args.preview)
        window.add_events(Gdk.EventMask.KEY_PRESS_MASK | Gdk.EventMask.BUTTON_PRESS_MASK |
                               Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.SCROLL_MASK)
        for event in ('key-press-event', 'button-press-event', 'scroll-event'):
            window.connect(event, lambda *_: self.close_all())
        window.connect('motion-notify-event', self.motion)
        window.connect('delete-event', lambda *_: self.close_all())
        area = Gtk.DrawingArea()
        area.connect('draw', self.draw, rectangle)
        window.add(area)
        if not self.args.preview:
            if monitor_index is None:
                window.fullscreen()
            else:
                window.fullscreen_on_monitor(window.get_screen(), monitor_index)
        window.show_all()
        window.get_window().set_cursor(Gdk.Cursor.new_for_display(
            window.get_display(), Gdk.CursorType.BLANK_CURSOR))
        self.views.append((window, area))
        self.window, self.area = window, area
        if self.args.span_monitors:
            area.add_tick_callback(lambda area, *_: (area.queue_draw(), True)[1])

    def close_all(self):
        self.quit()
        if not self.args.preview:
            # Same process marker used by Omarchy lock and stock screensavers.
            subprocess.run(['pkill', '-f', '[o]rg.omarchy.screensaver'], check=False)
        return True

    def motion(self, _, event):
        position = (event.x_root, event.y_root)
        if time.monotonic()-self.start > 1 and self.pointer is not None and position != self.pointer:
            self.close_all()
        self.pointer = position
        return True

    def check_focus(self):
        if time.monotonic()-self.start < 2:
            return True
        position = hypr('cursorpos', '-j')
        if position:
            if self.global_pointer is not None and position != self.global_pointer:
                self.close_all()
                return False
            self.global_pointer = position
        active = hypr('activewindow', '-j')
        if active:
            try:
                if json.loads(active).get('class') != 'org.omarchy.screensaver':
                    self.close_all()
                    return False
            except (ValueError, AttributeError):
                pass
        return True

    def tick(self, *_):
        now = time.monotonic()
        if self.args.duration and now-self.start >= self.args.duration:
            self.close_all()
            return False
        w, h = self.area.get_allocated_width(), self.area.get_allocated_height()
        dims = grid(w, h, self.args.cell_size)
        if self.topology is None and (self.game is None or dims != (self.game.width, self.game.height)):
            self.game = Arena(*dims, seed=self.args.seed, elapsed=now-self.start)
            self.previous = {}
            self.last_step = now
            self.sparks = []
        if now-self.last_step >= 1/self.args.speed:
            self.previous = {identity: (actor, list(actor.body))
                             for identity, actor in self.game.snakes.items()}
            for food in self.game.step(now-self.start):
                self.sparks.append((*food, now))
            self.last_step = now
        self.sparks = [s for s in self.sparks if now-s[2] < .6]
        self.area.queue_draw()
        return True

    def draw(self, area, cr, rectangle=None):
        if self.game:
            now = time.monotonic()
            fraction = min(1, (now-self.last_step)*self.args.speed)
            cr.save()
            if self.topology:
                if rectangle is None:
                    # Windowed overview of the actual monitor arrangement.
                    xs, ys = self.topology.x_edges, self.topology.y_edges
                    x, y, w, h = xs[0], ys[0], xs[-1]-xs[0], ys[-1]-ys[0]
                    scale = min(area.get_allocated_width()/w, area.get_allocated_height()/h)
                    cr.translate((area.get_allocated_width()-w*scale)/2,
                                 (area.get_allocated_height()-h*scale)/2)
                    cr.scale(scale, scale)
                    cr.translate(-x, -y)
                else:
                    x, y, w, h = rectangle
                    cr.scale(area.get_allocated_width()/w, area.get_allocated_height()/h)
                    cr.translate(-x, -y)
            render_arena(cr, self.game, self.previous, fraction,
                   area.get_allocated_width(), area.get_allocated_height(), now, self.sparks,
                   topology=self.topology, elapsed=now-self.start)
            cr.restore()
        else:
            cr.set_source_rgb(0, 0, 0)
            cr.paint()
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--span-monitors', action='store_true',
                        help='share one arena across the active monitor layout')
    parser.add_argument('--duration', type=float)
    parser.add_argument('--seed', type=int)
    parser.add_argument('--speed', type=float, default=14)
    parser.add_argument('--cell-size', type=int, default=28, help='approximate cell size in logical pixels')
    parser.add_argument('--app-id', default='org.omarchy.screensaver', choices=['org.omarchy.screensaver'])
    args = parser.parse_args()
    if not 1 <= args.speed <= 120 or not 12 <= args.cell_size <= 100:
        parser.error('speed must be 1–120 and cell size 12–100')
    GLib.set_prgname('org.omarchy.screensaver')
    Saver(args).run([])
