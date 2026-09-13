import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from engine import (
    World,
    Vec,
    Shot,
    Saucer,
    MAX_ROCKS,
    MAX_PARTICLES,
    segment_hit,
    intercept,
)


class PhysicsTests(unittest.TestCase):
    def quiet(self):
        world = World(1979)
        world.rocks = []
        world.stream_timer = 999
        world.saucer_timer = 999
        world.ship.invulnerable = 0
        world.ship.velocity = Vec()
        world.autopilot = lambda dt: None
        return world

    def test_thrust_and_inertia_without_wrapping(self):
        world = self.quiet()
        world.ship.angle = 0
        world.ship.thrust = True
        for _ in range(120):
            world.step(1 / 120)
        self.assertAlmostEqual(world.ship.velocity.x, 195.5)
        velocity = world.ship.velocity.x
        world.ship.thrust = False
        for _ in range(120):
            world.step(1 / 120)
        self.assertAlmostEqual(world.ship.velocity.x, velocity)
        world.ship.position = Vec(100000, -100000)
        world.step(1 / 120)
        self.assertGreater(world.ship.position.x, 100000)
        self.assertLess(world.ship.position.y, -99000)

    def test_camera_follows_without_pin_to_world_edges(self):
        world = self.quiet()
        world.ship.position = Vec(1e8, -1e8)
        for _ in range(240):
            world.step(1 / 120)
        self.assertLess((world.camera - world.ship.position).length(), 250000)
        for _ in range(240):
            world.step(1 / 120)
        self.assertLess((world.camera - world.ship.position).length(), 500)

    def test_large_medium_small_split_and_scores(self):
        world = self.quiet()
        large = world.make_rock(Vec(500, 500), 2, Vec(12, 0))
        world.rocks = [large]
        world.split_rock(large)
        self.assertEqual(len(world.rocks), 2)
        self.assertEqual([r.tier for r in world.rocks], [1, 1])
        for r in list(world.rocks):
            world.split_rock(r)
        self.assertEqual(len(world.rocks), 4)
        self.assertTrue(all(r.tier == 0 for r in world.rocks))
        for r in list(world.rocks):
            world.split_rock(r)
        self.assertEqual(world.rocks, [])
        self.assertEqual(world.score, 20 + 2 * 50 + 4 * 100)

    def test_player_shot_limit_and_cooldown(self):
        world = self.quiet()
        for _ in range(10):
            world.fire_timer = 0
            world.fire()
        self.assertEqual(len(world.shots), 4)
        world.shots = []
        world.fire_timer = 0
        world.fire()
        world.fire()
        self.assertEqual(len(world.shots), 1)

    def test_swept_shot_collision_cannot_tunnel(self):
        world = self.quiet()
        world.ship.position = Vec(-1000, 0)
        world.rocks = [world.make_rock(Vec(50, 0), 0, Vec())]
        world.shots = [Shot(Vec(0, 0), Vec(10000, 0))]
        world.step(0.01)
        self.assertEqual(world.score, 100)
        self.assertEqual(world.rocks, [])
        self.assertEqual(world.shots, [])

    def test_earliest_rock_gets_hit(self):
        world = self.quiet()
        world.ship.position = Vec(-1000, 0)
        near = world.make_rock(Vec(40, 0), 0, Vec())
        far = world.make_rock(Vec(80, 0), 0, Vec())
        world.rocks = [far, near]
        world.shots = [Shot(Vec(), Vec(10000, 0))]
        world.step(0.01)
        self.assertEqual(world.rocks, [far])

    def test_death_loop_resets_flight_and_score(self):
        world = self.quiet()
        world.score = 1234
        world.destroy_ship()
        self.assertTrue(world.dead)
        self.assertEqual(world.deaths, 1)
        world.step(3)
        self.assertFalse(world.dead)
        self.assertEqual(world.session, 1)
        self.assertEqual(world.score, 0)
        self.assertGreater(world.ship.invulnerable, 0)

    def test_spawn_protection_prevents_immediate_death(self):
        world = World(1)
        world.destroy_ship()
        self.assertFalse(world.dead)
        world.ship.invulnerable = 0
        world.destroy_ship()
        world.destroy_ship()
        self.assertEqual(world.deaths, 1)

    def test_hostile_shot_destroys_ship(self):
        world = self.quiet()
        world.shots = [Shot(Vec(-30, 0), Vec(1000, 0), hostile=True)]
        world.step(0.05)
        self.assertTrue(world.dead)

    def test_hostile_shot_splits_rocks_without_player_points(self):
        world = self.quiet()
        world.ship.position = Vec(-1000, 0)
        world.rocks = [world.make_rock(Vec(50, 0), 2, Vec())]
        world.shots = [Shot(Vec(), Vec(10000, 0), hostile=True)]
        world.step(0.01)
        self.assertEqual(world.score, 0)
        self.assertEqual(len(world.rocks), 2)

    def test_saucer_hit_and_scores(self):
        for small, points in [(False, 200), (True, 1000)]:
            world = self.quiet()
            world.ship.position = Vec(-1000, 0)
            world.saucer = Saucer(Vec(50, 0), Vec(), small)
            world.shots = [Shot(Vec(), Vec(10000, 0))]
            world.step(0.01)
            self.assertIsNone(world.saucer)
            self.assertEqual(world.score, points)

    def test_segment_and_intercept_math(self):
        self.assertAlmostEqual(segment_hit(Vec(), Vec(100, 0), Vec(50, 0), 10), 0.4)
        self.assertIsNone(segment_hit(Vec(), Vec(10, 0), Vec(50, 20), 10))
        self.assertEqual(segment_hit(Vec(), Vec(), Vec(), 10), 0)
        aim = intercept(Vec(500, 0), Vec(0, 100))
        self.assertGreater(aim.y, 0)


class StreamingTests(unittest.TestCase):
    def test_sector_generation_is_deterministic(self):
        a, b = World(1979), World(1979)
        self.assertEqual(
            [(r.position, r.outline) for r in a.rocks],
            [(r.position, r.outline) for r in b.rocks],
        )
        self.assertNotEqual(a.sector_seed(100000, 1), a.sector_seed(100001, 1))

    def test_streaming_culls_old_space_and_bounds_memory(self):
        world = World(2)
        initial = {tuple((r.position.x, r.position.y)) for r in world.rocks}
        for index in range(120):
            world.ship.position = world.camera = Vec(index * 10000, index * -8000)
            world.stream()
            self.assertGreater(len(world.rocks), 0)
            self.assertLessEqual(len(world.rocks), MAX_ROCKS)
            self.assertLessEqual(len(world.sectors), 512)
        self.assertFalse(
            initial.intersection({(r.position.x, r.position.y) for r in world.rocks})
        )

    def test_profile_resize_preserves_world_and_flight(self):
        world = World(1)
        position = world.ship.position
        for width, height in [(1600, 900), (3200, 900), (900, 1600)]:
            world.resize(width, height)
            self.assertEqual(world.ship.position, position)
            self.assertEqual((world.width, world.height), (width, height))

    def test_autonomous_two_minute_run(self):
        world = World(1979)
        combat_seconds = 0
        for _ in range(120 * 120):
            if world.warp_remaining == 0:
                combat_seconds += 1 / 120
            world.step(1 / 120)
        # Compare combat activity per flight time; warp pauses weapons and rocks.
        self.assertGreater(world.shots_fired, 40 * combat_seconds / 120)
        self.assertGreater(world.rocks_hit, 30 * combat_seconds / 120)
        self.assertGreater(world.total_distance, 10000)
        # Camera framing changes streamed encounters; surviving this seed is
        # valid. Death/restart behavior is covered with forced collisions above.
        self.assertLessEqual(len(world.rocks), MAX_ROCKS)
        self.assertLessEqual(len(world.sparks), MAX_PARTICLES)
        self.assertLessEqual(len(world.shots), 32)
        self.assertTrue(math.isfinite(world.camera.x))


if __name__ == "__main__":
    unittest.main()
