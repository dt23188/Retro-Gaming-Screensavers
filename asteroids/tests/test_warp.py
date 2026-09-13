from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import cairo
from engine import World, CorePart, Vec, WARP_DURATION, MAX_PARTS
from render import render


class WarpTests(unittest.TestCase):
    def test_opening_warp_arrives_at_belt_and_consumes_intro_cores(self):
        w=World(42,start_in_warp=True)
        self.assertEqual(w.warp_remaining,15)
        self.assertEqual(w.parts_collected,0)
        for _ in range(61):w.advance(.25)
        self.assertFalse(w.opening_warp)
        self.assertEqual(w.warps,1)
        self.assertEqual(w.core_parts,0)
        self.assertFalse(w.dead)
        self.assertGreater(len(w.rocks),40)

    def test_departure_keeps_camera_continuous_then_rushes_and_centers(self):
        import math
        for width,height in ((360,640),(1024,288)):
            w=World(42,width,height)
            w.ship.velocity=Vec(220,75)
            w.ship.angle=math.pi
            camera=Vec(w.camera.x,w.camera.y)
            w.core_parts=5;w.start_warp()
            self.assertEqual(w.camera,camera)
            vector=(w.warp_destination-w.warp_origin).unit()
            self.assertAlmostEqual(vector.x,w.ship.velocity.unit().x)
            self.assertAlmostEqual(vector.y,w.ship.velocity.unit().y)
            w.update_warp(.8)
            offset=w.ship.position-w.camera
            self.assertGreater(offset.dot(vector),50)
            self.assertLessEqual(abs(offset.x),width*.38+1e-6)
            self.assertLessEqual(abs(offset.y),height*.38+1e-6)
            w.update_warp(1.8)
            self.assertAlmostEqual((w.ship.position-w.camera).length(),0, places=5)
            self.assertAlmostEqual(w.ship.angle,w.warp_heading)

    def test_fifth_pickup_triggers_warp_and_four_do_not(self):
        w = World(1979)
        w.parts = []
        for count in range(1, 6):
            w.parts.append(CorePart(Vec(w.ship.position.x, w.ship.position.y)))
            w.collect_parts(1 / 120)
            self.assertEqual(w.core_parts, count)
            self.assertEqual(w.warp_remaining > 0, count == 5)
        self.assertEqual(w.parts_collected, 5)
        self.assertFalse(w.start_warp())

    def test_warp_arrival_preserves_score_and_changes_fleet_every_time(self):
        w = World(42)
        w.score = 1230
        for _ in range(6):
            old_fleet = w.zone_fleet
            origin = Vec(w.ship.position.x, w.ship.position.y)
            w.core_parts = 5
            self.assertTrue(w.start_warp())
            for _ in range(int(WARP_DURATION / 0.25) - 1):
                w.advance(0.25)
            self.assertGreater(w.warp_remaining, 0)
            w.ship.invulnerable = 0
            w.destroy_ship()
            self.assertFalse(w.dead)
            w.advance(0.25)
            w.advance(0.01)
            self.assertEqual(w.warp_remaining, 0)
            self.assertNotEqual(old_fleet, w.zone_fleet)
            self.assertGreater((w.ship.position - origin).length(), 89999)
            self.assertEqual(w.score, 1230)
            self.assertEqual(w.core_parts, 0)
            self.assertGreater(w.ship.invulnerable, 0)
            self.assertTrue(w.rocks)
        self.assertEqual(w.warps, 6)

    def test_autopilot_collects_and_warps_without_injected_pickups(self):
        w = World(1979)
        for _ in range(1440):
            w.advance(0.25)
            self.assertLessEqual(len(w.parts), MAX_PARTS)
        self.assertGreaterEqual(w.parts_collected, 5)
        self.assertGreaterEqual(w.warps, 1)
        self.assertGreater(w.shots_fired, 0)

    def test_parts_survive_repeated_destruction_until_fifth_pickup(self):
        w = World(1979)
        for count in range(1, 5):
            w.parts = [CorePart(Vec(w.ship.position.x, w.ship.position.y))]
            w.collect_parts(1 / 120)
            self.assertEqual(w.core_parts, count)
            w.ship.invulnerable = 0
            w.destroy_ship()
            self.assertTrue(w.dead)
            for _ in range(12):
                w.advance(0.25)
            self.assertFalse(w.dead)
            self.assertEqual(w.core_parts, count)
        w.parts = [CorePart(Vec(w.ship.position.x, w.ship.position.y))]
        w.collect_parts(1 / 120)
        self.assertEqual(w.warp_remaining, 15.0)

    def test_powerups_grant_shield_and_homing_missiles(self):
        w = World(1979)
        w.parts = [CorePart(Vec(), kind="shield")]
        w.collect_parts(1 / 120)
        self.assertTrue(w.activate_shield())
        w.ship.invulnerable = 0
        w.destroy_ship()
        self.assertFalse(w.dead)
        self.assertEqual(w.core_parts, 0)
        w.parts = [CorePart(Vec(), kind="missile")]
        w.collect_parts(1 / 120)
        self.assertEqual(w.missile_ammo, 8)
        w.fire()
        self.assertFalse(w.shots[-1].missile)
        self.assertEqual(w.missile_ammo, 8)
        w.shield_remaining = 0
        w.destroy_ship()
        self.assertTrue(w.dead)

    def test_no_cores_spawn_before_the_collection_clock(self):
        w = World(1979)
        # Enemy loot can legitimately grant an early core. Isolate the timed
        # spawn here instead of relying on the camera's seeded combat outcome.
        w.saucer_timer = 999
        for _ in range(120):
            w.advance(.25)
        self.assertEqual(w.parts_collected, 0)
        self.assertFalse(any(p.kind == "core" for p in w.parts))

    def test_warp_rendering_fits_portrait_and_ultrawide(self):
        w = World(1979)
        w.core_parts = 5
        w.start_warp()
        w.advance(0.25)
        for width, height in [(360, 640), (1024, 288)]:
            w.resize(width, height)
            surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
            render(cairo.Context(surface), w, width, height)
            surface.flush()
            data = bytes(surface.get_data())
            self.assertGreater(
                sum(data[i : i + 3] != b"\0\0\0" for i in range(0, len(data), 4)), 500
            )


if __name__ == "__main__":
    unittest.main()
