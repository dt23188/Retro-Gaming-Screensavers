from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from engine import FLEET_COLORS, Saucer, Shot, TERRITORY_RIVALS, Vec, World


class RivalFleetTests(unittest.TestCase):
    def world(self):
        w = World(1979)
        w.warps = 2
        w.rocks, w.parts, w.shots = [], [], []
        w.saucer_timer = w.rival_timer = w.stream_timer = 999
        w.ship.position, w.ship.velocity = Vec(0, 400), Vec()
        w.autopilot = lambda dt: None
        w.choose_powerups = lambda dt: None
        w.zone_fleet = 'ring'
        w.saucer = Saucer(Vec(300, 0), Vec(), False, kind='ring', cooldown=999)
        w.rival = Saucer(Vec(), Vec(), False, kind='raider', cooldown=999)
        return w

    def test_rival_identity_depends_on_territory(self):
        for territory in FLEET_COLORS:
            with self.subTest(territory=territory):
                w = self.world()
                w.zone_fleet = w.saucer.kind = territory
                w.rival = None
                w.rival_timer = 0
                w.update_saucer(.01)
                self.assertEqual(w.rival.kind, TERRITORY_RIVALS[territory])
                self.assertNotEqual(w.rival.kind, territory)
                self.assertLess(w.rival.life, w.saucer.life)
                self.assertGreaterEqual(w.rival_timer, 26)
                first = w.rival
                w.rival_timer = 0
                w.update_saucer(.01)
                self.assertIs(w.rival, first)
                self.assertEqual(len(w.rival_fleet), 2)
                self.assertEqual(len(w.enemies), 3)

    def test_rival_requires_resident_and_living_player(self):
        for state in ('no_resident', 'dead', 'warp'):
            with self.subTest(state=state):
                w = self.world()
                w.rival = None
                w.rival_timer = 0
                if state == 'no_resident':
                    w.saucer = None
                elif state == 'dead':
                    w.dead = True
                else:
                    w.warp_remaining = 5
                w.update_saucer(.01)
                self.assertIsNone(w.rival)

    def test_fleets_prioritize_each_other_over_closer_player(self):
        w = self.world()
        w.ship.position = Vec(0, 80)
        self.assertIs(w.fleet_target(w.rival), w.saucer)
        self.assertIs(w.fleet_target(w.saucer), w.rival)
        w.rival.cooldown = 0
        w.update_saucer(.01)
        self.assertGreater(w.rival.velocity.x, 0)
        self.assertAlmostEqual(w.rival.velocity.y, 0)
        shot = w.shots[0]
        self.assertEqual(shot.faction, 'raider')
        self.assertGreater(shot.velocity.x, 400)
        self.assertAlmostEqual(shot.velocity.y, 0)
        w.saucer = None
        self.assertIs(w.fleet_target(w.rival), w.ship)

    def test_rival_shots_kill_resident_without_player_score(self):
        w = self.world()
        w.shots = [Shot(Vec(240, 0), Vec(1000, 0), hostile=True, faction='raider')]
        w.step(.1)
        self.assertIsNone(w.saucer)
        self.assertIsNotNone(w.rival)
        self.assertEqual(w.score, 0)
        self.assertEqual(w.shots, [])

    def test_resident_can_destroy_rival_and_friendly_fire_is_ignored(self):
        w = self.world()
        w.shots = [Shot(Vec(-60, 0), Vec(1000, 0), hostile=True, faction='raider')]
        w.step(.1)
        self.assertIsNotNone(w.rival)
        w.shots = [Shot(Vec(-60, 0), Vec(1000, 0), hostile=True, faction='ring')]
        w.step(.1)
        self.assertIsNone(w.rival)
        self.assertIsNotNone(w.saucer)
        self.assertEqual(w.score, 0)

    def test_asteroid_blocks_ship_to_ship_shot(self):
        w = self.world()
        w.rocks = [w.make_rock(Vec(150, 0), 0, Vec())]
        w.shots = [Shot(Vec(50, 0), Vec(3000, 0), hostile=True, faction='raider')]
        w.step(.1)
        self.assertIsNotNone(w.saucer)
        self.assertEqual(w.rocks, [])
        self.assertEqual(w.score, 0)

    def test_rival_shield_absorbs_resident_shot(self):
        w = self.world()
        w.rival.shield_remaining = 5
        w.shots = [Shot(Vec(-60, 0), Vec(1000, 0), hostile=True, faction='ring')]
        w.step(.1)
        self.assertIsNotNone(w.rival)
        self.assertEqual(w.shots, [])

    def test_player_can_hit_rival_with_blaster_or_missile(self):
        for missile in (False, True):
            with self.subTest(missile=missile):
                w = self.world()
                w.saucer = None
                w.shots = [Shot(Vec(-60, 0), Vec(1000, 0), missile=missile)]
                w.step(.1)
                self.assertIsNone(w.rival)
                self.assertEqual(w.score, 200)

    def test_enemy_missile_homes_on_opposing_fleet_then_player(self):
        w = self.world()
        w.rival.missile_ammo = 1
        w.rival.cooldown = 0
        w.update_saucer(.01)
        shot = w.shots[0]
        self.assertTrue(shot.missile)
        w.saucer.position = Vec(300, -200)
        w.step(.05)
        self.assertLess(shot.velocity.y, 0)
        w.saucer = None
        w.ship.position = Vec(300, 400)
        w.step(.05)
        self.assertGreater(shot.velocity.y, 0)

    def test_player_missile_is_not_blocked_by_enemy_missile(self):
        w = self.world()
        w.missile_ammo = 1
        w.shots = [Shot(Vec(), Vec(), hostile=True, missile=True, faction='ring')]
        self.assertTrue(w.launch_missile())

    def test_player_blast_hits_both_fleets(self):
        w = self.world()
        w.blast_charges = 1
        w.activate_blast()
        w.update_blast(1.3)
        self.assertEqual(w.enemies, [])
        self.assertEqual(w.score, 400)

    def test_rivals_clear_on_warp_and_reset(self):
        w = self.world()
        w.core_parts = 5
        self.assertTrue(w.start_warp())
        self.assertEqual(w.enemies, [])
        w.finish_warp()
        self.assertIsNone(w.rival)
        self.assertGreater(w.rival_timer, 0)
        w.rival = Saucer(Vec(), Vec(), False)
        w.reset()
        self.assertIsNone(w.rival)

    def test_rivals_spawn_less_often_than_residents(self):
        w = self.world()
        w.saucer = w.rival = None
        w.saucer_timer, w.rival_timer = 0, 22
        # Isolate spawn pacing from combat, pickups and death.
        w.update_fleet_ship = lambda enemy, dt: self.expire(w, enemy, dt)
        with patch.object(w, 'spawn_fleet_ship', wraps=w.spawn_fleet_ship) as spawn:
            for _ in range(1800):
                w.update_saucer(.1)
            resident = sum(c.args[0] == 'ring' for c in spawn.call_args_list)
            rival = sum(c.args[0] == 'raider' for c in spawn.call_args_list)
        self.assertGreater(rival, 0)
        self.assertLess(rival, resident)

    @staticmethod
    def expire(w, enemy, dt):
        enemy.life -= dt
        if enemy.life <= 0:
            w.remove_enemy(enemy)


if __name__ == '__main__':
    unittest.main()
