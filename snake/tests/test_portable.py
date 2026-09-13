import collections
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtGui import QImage, QPainter
    from portable import parse_args, Simulation
    import qt_cairo
    from drawing import render_arena
    from snake import Snake
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'PySide6 not installed in this interpreter')
class PortableTests(unittest.TestCase):
    def test_windows_screensaver_arguments(self):
        self.assertFalse(parse_args(['/S']).configure)
        self.assertTrue(parse_args(['/c:1234']).configure)
        self.assertEqual(parse_args(['/p', '1234']).embed, 1234)
        self.assertEqual(parse_args(['/p:1234']).embed, 1234)
        self.assertTrue(parse_args(['--span-monitors']).span)
        self.assertFalse(parse_args(['--independent-monitors']).span)

    def test_qt_draws_one_snake_continuously_across_two_viewports(self):
        rectangles = [(0,0,400,300), (400,100,400,300)]
        sim = Simulation(rectangles, SimpleNamespace(cell_size=40, seed=42))
        actor = Snake(collections.deque([(10,4),(9,4),(8,4),(7,4)]), 0, [0])
        sim.game.snakes = {0: actor}
        sim.game.foods = set()
        previous = {0: (actor, [(9,4),(8,4),(7,4),(6,4)])}
        def draw(width, height, x=0, y=0):
            image = QImage(width, height, QImage.Format.Format_RGB32)
            painter = QPainter(image)
            painter.translate(-x,-y)
            try:
                render_arena(qt_cairo.Context(painter), sim.game, previous, .5,
                             width, height, 0, topology=sim.topology, backend=qt_cairo)
            finally:
                painter.end()
            return image
        whole = draw(800,400)
        for x,y,w,h in rectangles:
            self.assertEqual(draw(w,h,x,y), whole.copy(x,y,w,h))
        seam_y = round(sim.topology.center((10,4))[1])
        self.assertGreater(whole.pixelColor(399,seam_y).green(), 0)
        self.assertGreater(whole.pixelColor(400,seam_y).green(), 0)

    def test_qt_food_and_glow_expire(self):
        sim = Simulation([(0,0,480,320)], SimpleNamespace(cell_size=40, seed=42))
        sim.game.snakes = {0: Snake(collections.deque([(0,0),(1,0),(2,0),(3,0)]),0,[0])}
        sim.game.foods = {(8,5)}
        sim.game.food_born = {(8,5): 0}
        brightness=[]
        for elapsed in (25,27.5,30):
            image=QImage(480,320,QImage.Format.Format_RGB32)
            painter=QPainter(image)
            try:
                render_arena(qt_cairo.Context(painter),sim.game,{},1,480,320,0,
                             topology=sim.topology,elapsed=elapsed,backend=qt_cairo)
            finally:
                painter.end()
            brightness.append(sum(image.pixelColor(x,y).red() for x in range(305,375)
                                  for y in range(185,255)))
        self.assertGreater(brightness[0],brightness[1])
        self.assertGreater(brightness[1],brightness[2])
        self.assertEqual(brightness[2],0)


if __name__ == '__main__':
    unittest.main()
