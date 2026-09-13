from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import cairo
from engine import World
from render import render


class RenderTests(unittest.TestCase):
    def test_black_canvas_and_visible_ship(self):
        world = World(1979)
        world.rocks = []
        surface = cairo.ImageSurface(cairo.FORMAT_RGB24, 900, 900)
        render(cairo.Context(surface), world, 900, 900)
        surface.flush()
        data = bytes(surface.get_data())
        colored = sum(data[i : i + 3] != b"\0\0\0" for i in range(0, len(data), 4))
        self.assertGreater(colored, 200)
        self.assertLess(colored, 900 * 900 * 0.05)

    def test_portrait_ultrawide_and_destruction_frames(self):
        world = World(4)
        for width, height in [(360, 640), (1024, 288), (720, 450)]:
            world.resize(width, height)
            world.ship.invulnerable = 0
            world.destroy_ship()
            surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
            render(cairo.Context(surface), world, width, height)
            self.assertEqual(surface.get_width(), width)


if __name__ == "__main__":
    unittest.main()
