"""A desktop has one simulation, including across monitor seams and gaps."""
from pathlib import Path
import os
import sys
import unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'asteroids/src'))
import retro_portable as host
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication
from engine import Vec


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def desktop(self, rectangles):
        desktop = host.AsteroidsDesktop([QRect(*r) for r in rectangles], seed=42)
        w = desktop.world
        w.warp_remaining = 0
        w.opening_warp = False
        w.ship.position = w.camera = Vec()
        w.ship.invulnerable = 100
        w.ship.thrust = False
        w.rocks = []; w.parts = []; w.saucer = None
        w.stream_timer = w.saucer_timer = 999
        w.autopilot = lambda dt: None
        return desktop

    def move(self, desktop, velocity, seconds):
        w = desktop.world
        w.ship.velocity = velocity
        for _ in range(round(seconds * 120)):
            w.step(1 / 120)
        return w.ship.position - w.camera + Vec(w.width / 2, w.height / 2)

    def test_stacked_user_layout_crosses_seam_and_recenters(self):
        d = self.desktop([(0, 0, 3840, 2160), (200, 2160, 3440, 1440)])
        self.assertEqual((d.world.width, d.world.height), (3840, 3600))
        below = self.move(d, Vec(0, 280), 5)
        self.assertGreater(below.y, 2160)
        above = self.move(d, Vec(0, -280), 8)
        self.assertLess(above.y, 2160)
        stopped = self.move(d, Vec(), 4)
        self.assertLess((stopped - Vec(1920, 1800)).length(), 1)

    def test_side_by_side_and_negative_coordinates(self):
        d = self.desktop([(-1920, -100, 1920, 1080), (0, -100, 1920, 1080)])
        self.assertEqual(d.regions, [QRect(0, 0, 1920, 1080), QRect(1920, 0, 1920, 1080)])
        self.assertGreater(self.move(d, Vec(280, 0), 5).x, 2500)
        self.assertLess(self.move(d, Vec(-280, 0), 10).x, 1500)
        for velocity in (Vec(280, 0), Vec(-280, 0), Vec(0, 280), Vec(0, -280)):
            point = self.move(d, velocity, 20)
            self.assertTrue(.1*d.world.width-1 <= point.x <= .9*d.world.width+1)
            self.assertTrue(.1*d.world.height-1 <= point.y <= .9*d.world.height+1)

    def test_uncovered_desktop_corner_is_not_a_ship_hiding_place(self):
        d = self.desktop([(0, 0, 1200, 700), (400, 700, 400, 700)])
        w = d.world
        w.ship.position = Vec(100, 1200) - Vec(w.width/2, w.height/2)
        w.constrain_camera()
        point = w.ship.position - w.camera + Vec(w.width/2, w.height/2)
        self.assertTrue(any(r.x() <= point.x <= r.x()+r.width() and
                            r.y() <= point.y <= r.y()+r.height() for r in d.regions))
        # An internal seam itself must not clamp/recenter the camera.
        w.ship.position = Vec(600, 700) - Vec(w.width/2, w.height/2)
        w.camera = Vec()
        w.constrain_camera()
        self.assertEqual(w.camera, Vec())

    def test_monitor_crops_align_and_paint_does_not_advance_world(self):
        d = self.desktop([(0, 0, 320, 360), (320, 0, 320, 360)])
        w = d.world
        w.ship.invulnerable = 0
        w.ship.angle = 0
        w.fire()
        image = QImage(640, 360, QImage.Format.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        host.art.render(host.backend.Context(painter), w, 640, 360)
        painter.end()
        before = (w.time, w.ship.position, w.shots[0].position)
        for index, region in enumerate(d.regions):
            crop = QImage(region.size(), image.format())
            painter = QPainter(crop)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            d.paint(painter, index)
            painter.end()
            expected = image.copy(region)
            # Translation/clipping can round an antialiased edge by one level.
            self.assertLessEqual(max(abs(a-b) for a,b in
                zip(bytes(crop.constBits()), bytes(expected.constBits()))), 1)
        self.assertEqual((w.time, w.ship.position, w.shots[0].position), before)
        d.advance(d.last + .1)
        self.assertAlmostEqual(w.time, before[0] + .1)
        self.assertGreater(w.shots[0].position.x, before[2].x)

    def test_single_monitor_preserves_camera_range(self):
        d = self.desktop([(200, 2160, 3440, 1440)])
        point = self.move(d, Vec(280, 0), 5)
        self.assertLess((point - Vec(1720, 720)).length(), 1440*.18)


if __name__ == '__main__':
    unittest.main()
