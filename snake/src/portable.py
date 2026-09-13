#!/usr/bin/env python3
"""Snake Screensaver for Windows and Linux (Qt/PySide6)."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time

from PySide6.QtCore import QTimer, Qt, QRect
from PySide6.QtGui import QCursor, QPainter, QWindow
from PySide6.QtWidgets import QApplication, QWidget, QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox, QLabel

from snake import Arena
from topology import Topology
from drawing import render_arena
import qt_cairo


def config_path():
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'SnakeScreensaver' / 'settings.json'
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config')) / 'snake-screensaver' / 'settings.json'


def settings():
    try:
        value = json.loads(config_path().read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def parse_args(argv):
    # Windows launches .scr files with /s, /c[:HWND], or /p HWND.
    translated = list(argv)
    if translated and translated[0].lower().split(':')[0] in ('/s', '/c', '/p'):
        mode, _, handle = translated[0].lower().partition(':')
        if mode == '/s':
            translated = []
        elif mode == '/c':
            translated = ['--configure']
        else:
            handle = handle or (translated[1] if len(translated) > 1 else '0')
            translated = ['--embed', handle]
    elif not translated and sys.platform == 'win32':
        translated = ['--configure']
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--configure', action='store_true')
    parser.add_argument('--embed', type=int, default=0, help=argparse.SUPPRESS)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--span-monitors', dest='span', action='store_true')
    modes.add_argument('--independent-monitors', dest='span', action='store_false')
    parser.set_defaults(span=settings().get('span_monitors', True))
    parser.add_argument('--duration', type=float)
    parser.add_argument('--speed', type=float, default=14)
    parser.add_argument('--cell-size', type=int, default=28)
    parser.add_argument('--seed', type=int)
    args = parser.parse_args(translated)
    if not 1 <= args.speed <= 120 or not 12 <= args.cell_size <= 100:
        parser.error('speed must be 1–120 and cell size 12–100')
    if args.duration is not None and args.duration <= 0:
        parser.error('duration must be positive')
    return args


def configure():
    dialog = QDialog()
    dialog.setWindowTitle('Snake Screensaver')
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel('Competing snakes • Smooth motion • Fading food'))
    span = QCheckBox('Allow snakes to travel across touching displays')
    span.setChecked(settings().get('span_monitors', True))
    layout.addWidget(span)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = settings()
        data['span_monitors'] = span.isChecked()
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2)+'\n')
    return 0


def screen_rectangles(screens):
    rectangles = [(s.geometry().x(), s.geometry().y(), s.geometry().width(), s.geometry().height())
                  for s in screens]
    if sys.platform != 'win32':
        return rectangles
    # Qt logical screen sizes can leave artificial gaps between differently
    # scaled Windows monitors. Use the native desktop rectangles for topology;
    # each viewport still scales rendering to its own Qt logical dimensions.
    import ctypes
    from ctypes import wintypes
    class MonitorInfo(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', wintypes.RECT),
                    ('rcWork', wintypes.RECT), ('dwFlags', wintypes.DWORD),
                    ('szDevice', wintypes.WCHAR*32)]
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR,
                                      wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MonitorInfo)]
    user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT),
                                         callback_type, wintypes.LPARAM]
    native = {}
    @callback_type
    def record(handle, *_):
        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(info)
        if user32.GetMonitorInfoW(handle, ctypes.byref(info)):
            r = info.rcMonitor
            native[info.szDevice] = (r.left, r.top, r.right-r.left, r.bottom-r.top)
        return True
    user32.EnumDisplayMonitors(None, None, record, 0)
    # Avoid mixing native and logical coordinate spaces if names do not match.
    if all(s.name() in native for s in screens):
        return [native[s.name()] for s in screens]
    return rectangles


class Simulation:
    def __init__(self, rectangles, args):
        self.topology = Topology(rectangles, args.cell_size)
        self.game = Arena(self.topology.width, self.topology.height, args.seed, cells=self.topology.cells)
        self.previous = {}
        self.sparks = []
        self.last_step = time.monotonic()

    def advance(self, now, elapsed, speed):
        if now-self.last_step >= 1/speed:
            self.previous = {i: (s, list(s.body)) for i,s in self.game.snakes.items()}
            self.sparks.extend((*p,now) for p in self.game.step(elapsed))
            self.last_step = now
        self.sparks = [s for s in self.sparks if now-s[2] < .6]


class View(QWidget):
    def __init__(self, owner, simulation, screen, rectangle):
        super().__init__()
        self.owner, self.simulation, self.rectangle = owner, simulation, rectangle
        self.setWindowTitle('Snake Screensaver')
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.BlankCursor)
        if owner.args.preview or owner.args.embed:
            self.resize(1100, 700)
        else:
            self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint |
                                Qt.WindowType.WindowStaysOnTopHint)
            self.winId()
            self.windowHandle().setScreen(screen)
            self.setGeometry(screen.geometry())

    def paintEvent(self, _):
        now = time.monotonic()
        sim = self.simulation
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        try:
            if self.rectangle is None:
                xs, ys = sim.topology.x_edges, sim.topology.y_edges
                x, y, w, h = xs[0], ys[0], xs[-1]-xs[0], ys[-1]-ys[0]
                scale = min(self.width()/w, self.height()/h)
                painter.translate((self.width()-w*scale)/2, (self.height()-h*scale)/2)
                painter.scale(scale, scale)
            else:
                x, y, w, h = self.rectangle
                painter.scale(self.width()/w, self.height()/h)
            painter.translate(-x, -y)
            render_arena(qt_cairo.Context(painter), sim.game, sim.previous,
                         min(1, (now-sim.last_step)*self.owner.args.speed),
                         self.width(), self.height(), now, sim.sparks,
                         topology=sim.topology, elapsed=now-self.owner.start, backend=qt_cairo)
        finally:
            painter.end()

    def keyPressEvent(self, _):
        if not self.owner.args.embed:
            QApplication.quit()

    mousePressEvent = keyPressEvent
    wheelEvent = keyPressEvent

    def mouseMoveEvent(self, event):
        if not self.owner.args.embed and time.monotonic()-self.owner.start > 1:
            position = event.globalPosition().toPoint()
            if (position-self.owner.pointer).manhattanLength() > 3:
                QApplication.quit()

    def closeEvent(self, event):
        QApplication.quit()
        event.accept()


class Saver:
    def __init__(self, app, args):
        self.args, self.start = args, time.monotonic()
        self.pointer = QCursor.pos()
        screens = app.screens()
        rectangles = screen_rectangles(screens)
        self.simulations, self.views = [], []
        if args.embed:
            args.preview = True
            rectangles = [(0,0,640,480)]
        if args.span or args.preview:
            self.simulations.append(Simulation(rectangles, args))
        for screen, rectangle in zip(screens, rectangles):
            if not args.span and not args.preview:
                self.simulations.append(Simulation([rectangle], args))
            sim = self.simulations[0] if args.span or args.preview else self.simulations[-1]
            view = View(self, sim, screen, None if args.preview else rectangle)
            self.views.append(view)
            if args.preview:
                view.show()
                break
            view.showFullScreen()
        if args.embed:
            self.embed(self.views[0], args.embed)
        for screen in screens:
            screen.geometryChanged.connect(app.quit)
        app.screenAdded.connect(app.quit)
        app.screenRemoved.connect(app.quit)
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(8)
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: app.quit())

    def embed(self, view, handle):
        if sys.platform != 'win32':
            raise ValueError('embedded preview is only supported on Windows')
        import ctypes
        from ctypes import wintypes
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user32.IsWindow.argtypes = [wintypes.HWND]
        rect = wintypes.RECT()
        if not self.user32.GetClientRect(handle, ctypes.byref(rect)):
            raise ValueError('invalid Windows preview handle')
        self.foreign_parent = QWindow.fromWinId(handle)
        view.windowHandle().setParent(self.foreign_parent)
        view.setGeometry(QRect(0, 0, rect.right, rect.bottom))

    def tick(self):
        now = time.monotonic()
        if self.args.duration and now-self.start >= self.args.duration:
            QApplication.quit()
            return
        if self.args.embed and not self.user32.IsWindow(self.args.embed):
            QApplication.quit()
            return
        for sim in self.simulations:
            sim.advance(now, now-self.start, self.args.speed)
        for view in self.views:
            view.update()


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    app = QApplication([sys.argv[0]])
    app.setApplicationName('Snake Screensaver')
    app.setDesktopFileName('org.omarchy.screensaver')
    if args.configure:
        return configure()
    saver = Saver(app, args)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
