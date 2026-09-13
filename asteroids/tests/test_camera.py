"""Behavioral coverage for directional camera lag and safe screen framing."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from engine import World, Vec


class CameraTests(unittest.TestCase):
    def travel(self, world, velocity, seconds, hz=120):
        world.ship.velocity = velocity
        for _ in range(round(seconds * hz)):
            world.ship.position = world.ship.position + velocity * (1 / hz)
            world.update_camera(1 / hz)
        return world.ship.position - world.camera

    def test_ship_leads_in_all_directions_and_more_at_higher_speed(self):
        for angle in range(0, 360, 45):
            heading = Vec(math.cos(math.radians(angle)), math.sin(math.radians(angle)))
            offsets = []
            for speed in (60, 280):
                world = World(42, 1920, 1080)
                early = self.travel(world, heading * speed, .1)
                offset = self.travel(world, heading * speed, 5)
                self.assertGreater(offset.dot(heading), early.dot(heading))
                self.assertGreater(offset.dot(heading), speed * .6)
                self.assertAlmostEqual(offset.x * heading.y - offset.y * heading.x, 0)
                offsets.append(offset.length())
            self.assertGreater(offsets[1], offsets[0] * 3)

    def test_stop_recenters_and_reversal_passes_through_center(self):
        world = World(42)
        offset = self.travel(world, Vec(240, 0), 4)
        stopped = self.travel(world, Vec(), .1)
        self.assertGreater(stopped.x, 0)
        self.assertLess(stopped.x, offset.x)
        self.assertLess(self.travel(world, Vec(), 3).length(), .1)
        self.travel(world, Vec(240, 0), 4)
        self.assertGreater(self.travel(world, Vec(-240, 0), .1).x, 0)
        self.assertLess(self.travel(world, Vec(-240, 0), 3).x, -140)

    def test_portrait_ultrawide_and_resize_stay_inside_central_region(self):
        world = World(42)
        for width, height in ((3440, 1440), (360, 640), (1024, 288), (100, 100)):
            world.resize(width, height)
            for velocity in (Vec(300, 0), Vec(0, -300), Vec(-212, 212)):
                offset = self.travel(world, velocity, 3)
                self.assertLessEqual(offset.length(), min(width, height) * .18 + 1e-8)
                self.assertGreater(offset.dot(velocity), 0)

    def test_stationary_camera_easing_is_independent_of_update_rate(self):
        results = []
        for hz in (30, 60, 120):
            world = World(42)
            world.camera = Vec(-100, 50)
            results.append(self.travel(world, Vec(), 1, hz))
        for offset in results[1:]:
            self.assertAlmostEqual(offset.x, results[0].x)
            self.assertAlmostEqual(offset.y, results[0].y)

    def test_warp_cruise_moves_and_arrival_does_not_snap_to_center(self):
        world = World(42)
        world.ship.velocity = Vec(200, 100)
        world.core_parts = 5
        world.start_warp()
        world.update_warp(3)
        early = world.ship.position - world.camera
        world.update_warp(10)
        late = world.ship.position - world.camera
        self.assertGreater(late.length(), early.length() + 50)
        world.update_warp(1.99)
        before = world.ship.position - world.camera
        world.update_warp(.01)
        after = world.ship.position - world.camera
        self.assertLess((after - before).length(), 1)
        self.assertGreater(after.length(), 100)
        world.update_camera(1 / 120)
        self.assertLess((world.ship.position - world.camera - after).length(), 2)


if __name__ == '__main__':
    unittest.main()
