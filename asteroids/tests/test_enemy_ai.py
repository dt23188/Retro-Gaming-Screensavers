from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from engine import CorePart, Saucer, Shot, Vec, World


class EnemyAITests(unittest.TestCase):
    def world(self):
        w = World(1979)
        w.rocks, w.parts, w.shots = [], [], []
        w.stream_timer = w.saucer_timer = 999
        w.ship.position, w.ship.velocity = Vec(600, 0), Vec()
        w.autopilot = lambda dt: None
        w.choose_powerups = lambda dt: None
        w.saucer = Saucer(Vec(), Vec(0, 100), False, cooldown=100)
        return w

    def test_pursuit_changes_course_as_player_moves(self):
        w = self.world()
        for _ in range(120):
            w.update_saucer(1 / 120)
        self.assertGreater(w.saucer.position.x, 50)
        w.ship.position = Vec(-600, -600)
        for _ in range(240):
            w.update_saucer(1 / 120)
        self.assertLess(w.saucer.velocity.x, 0)
        self.assertLess(w.saucer.velocity.y, 0)
        self.assertLessEqual(w.saucer.velocity.length(), 220.001)

    def test_predicts_obstacle_and_steers_clear(self):
        w = self.world()
        w.saucer.velocity = Vec(200, 0)
        rock = w.make_rock(Vec(200, 0), 2, Vec())
        w.rocks = [rock]
        for _ in range(180):
            w.update_saucer(1 / 120)
            self.assertGreater((w.saucer.position - rock.position).length(),
                               rock.radius + w.saucer.radius)
        self.assertGreater(abs(w.saucer.position.y), 50)

    def test_enemy_aims_at_and_breaks_obstructing_rock(self):
        w = self.world()
        w.saucer.velocity = Vec(200, 0)
        w.saucer.cooldown = 0
        rock = w.make_rock(Vec(180, 0), 2, Vec())
        w.rocks = [rock]
        for _ in range(60):
            w.step(1 / 120)
        self.assertNotIn(rock, w.rocks)
        self.assertEqual(w.score, 0)
        self.assertEqual(w.rocks_hit, 0)

    def test_enemy_diverts_to_and_collects_powerup(self):
        w = self.world()
        pickup = CorePart(Vec(0, 200), kind='shield')
        core = CorePart(Vec(0, 20), kind='core')
        w.parts = [pickup, core]
        for _ in range(240):
            w.update_saucer(1 / 120)
        self.assertNotIn(pickup, w.parts)
        self.assertIn(core, w.parts)
        self.assertGreater(w.saucer.shield_remaining, 0)
        w.damage_enemy()
        self.assertIsNotNone(w.saucer)
        w.saucer.shield_remaining = 0
        w.damage_enemy()
        self.assertIsNone(w.saucer)

    def test_swept_pickup_and_enemy_missile_targets_player(self):
        w = self.world()
        w.parts = [CorePart(Vec(50, 0), kind='missile')]
        w.saucer.position = Vec(100, 0)
        w.collect_enemy_parts(w.saucer, Vec())
        self.assertEqual(w.saucer.missile_ammo, 4)
        w.saucer.cooldown = 0
        w.update_saucer(.01)
        shot = w.shots[0]
        self.assertTrue(shot.hostile and shot.missile)
        self.assertEqual(w.saucer.missile_ammo, 3)
        w.ship.position = Vec(600, 500)
        before = shot.velocity.y
        w.step(.05)
        self.assertGreater(shot.velocity.y, before)
        self.assertIsNotNone(w.saucer)

    def test_enemy_blast_clears_local_rocks_without_points(self):
        w = self.world()
        near = w.make_rock(Vec(100, 0), 0, Vec())
        far = w.make_rock(Vec(800, 0), 0, Vec())
        w.rocks = [near, far]
        w.parts = [CorePart(Vec(), kind='blast')]
        w.collect_enemy_parts(w.saucer, Vec())
        self.assertEqual(w.parts, [])
        self.assertEqual(w.rocks, [far])
        self.assertEqual(w.score, 0)

    def test_rock_blocks_hostile_shot_before_player(self):
        w = self.world()
        w.saucer = None
        w.ship.invulnerable = 0
        w.ship.position = Vec(100, 0)
        w.rocks = [w.make_rock(Vec(50, 0), 0, Vec())]
        w.shots = [Shot(Vec(), Vec(2000, 0), hostile=True)]
        w.step(.1)
        self.assertEqual(w.ship.hit_points, 2)
        self.assertEqual(w.rocks, [])

    def test_damage_grace_period_and_respawn_health(self):
        w = self.world()
        w.ship.invulnerable = 0
        w.damage_ship()
        w.damage_ship()
        self.assertEqual(w.ship.hit_points, 1)
        self.assertFalse(w.dead)
        w.ship.invulnerable = 0
        w.damage_ship()
        self.assertTrue(w.dead)
        w.step(3)
        self.assertEqual(w.ship.hit_points, 2)
        self.assertFalse(w.dead)


if __name__ == '__main__':
    unittest.main()
