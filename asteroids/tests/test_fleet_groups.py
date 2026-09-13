from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from engine import Saucer, Vec, World


class FleetGroupTests(unittest.TestCase):
    def world(self):
        w = World(1979)
        w.rocks, w.parts, w.shots = [], [], []
        w.ship.position = Vec(1500, 0)
        w.ship.velocity = Vec()
        w.saucer_timer = w.rival_timer = 999
        return w

    def test_rivals_unlock_only_after_second_completed_warp(self):
        w = self.world()
        for completed in range(3):
            self.assertEqual(w.warps, completed)
            w.saucer = Saucer(Vec(), Vec(), False, kind=w.zone_fleet)
            w.rival_timer = 0
            w.update_saucer(.01)
            self.assertEqual(len(w.rival_fleet), 2 if completed == 2 else 0)
            if completed < 2:
                w.core_parts = 5
                self.assertTrue(w.start_warp())
                w.update_saucer(.01)
                self.assertEqual(w.enemies, [])
                w.update_warp(15)

    def test_opening_warp_alone_does_not_unlock_rivals(self):
        w = World(1979, start_in_warp=True)
        w.update_warp(15)
        self.assertEqual(w.warps, 1)
        w.saucer_timer = w.rival_timer = 0
        w.update_saucer(.01)
        self.assertEqual(len(w.resident_fleet), 3)
        self.assertEqual(w.rival_fleet, [])

    def test_resident_group_has_one_more_ship_and_shared_entry(self):
        w = self.world()
        w.warps = 2
        w.saucer_timer = w.rival_timer = 0
        w.update_saucer(.01)
        self.assertEqual(len(w.resident_fleet), 3)
        self.assertEqual(len(w.rival_fleet), 2)
        for fleet in (w.resident_fleet, w.rival_fleet):
            self.assertEqual(len({member.kind for member in fleet}), 1)
            for follower in fleet[1:]:
                self.assertLess((follower.position - fleet[0].position).length(), 150)
                self.assertGreater((follower.position - fleet[0].position).length(), 100)
                self.assertLess((follower.velocity - fleet[0].velocity).length(), 6)

    def test_wingmates_follow_and_rejoin_after_displacement(self):
        w = self.world()
        w.resident_fleet = w.spawn_fleet_group(w.zone_fleet, 3)
        leader = w.saucer
        leader.position, leader.velocity = Vec(), Vec(200, 0)
        w.resident_fleet[1].position = Vec(-95, 90)
        w.resident_fleet[2].position = Vec(-95, -90)
        for member in w.resident_fleet:
            member.velocity = Vec(200, 0)
            member.cooldown = 999
        w.resident_fleet[1].position = Vec(-350, 260)
        initial = (w.resident_fleet[1].position - leader.position).length()
        for _ in range(600):
            w.update_saucer(1 / 120)
        distance = (w.resident_fleet[1].position - leader.position).length()
        self.assertLess(distance, initial)
        self.assertLess(distance, 230)
        self.assertGreater(leader.position.x, 500)
        for a, b in ((0, 1), (0, 2), (1, 2)):
            self.assertGreater((w.resident_fleet[a].position - w.resident_fleet[b].position).length(), 60)

    def test_leader_death_promotes_survivor_without_spawning_extra_group(self):
        w = self.world()
        w.resident_fleet = w.spawn_fleet_group(w.zone_fleet, 3)
        survivors = w.resident_fleet[1:]
        w.destroy_enemy(w.saucer, award=False)
        self.assertIs(w.saucer, survivors[0])
        w.saucer_timer = 0
        w.update_saucer(.01)
        self.assertEqual(w.resident_fleet, survivors)
        for enemy in list(w.resident_fleet):
            w.remove_enemy(enemy)
        w.update_saucer(.01)
        self.assertEqual(len(w.resident_fleet), 3)

    def test_all_group_members_clear_on_warp_and_reset(self):
        w = self.world()
        for action in ('warp', 'reset'):
            w.resident_fleet = w.spawn_fleet_group('ring', 3)
            w.rival_fleet = w.spawn_fleet_group('raider', 2)
            if action == 'warp':
                w.core_parts = 5
                w.start_warp()
            else:
                w.reset()
            self.assertEqual(w.enemies, [])

    def test_player_blast_and_damage_include_wingmates(self):
        w = self.world()
        w.ship.position = Vec()
        w.resident_fleet = [Saucer(Vec(100, y), Vec(), False, kind='ring')
                            for y in (-100, 0, 100)]
        w.rival_fleet = [Saucer(Vec(-100, y), Vec(), False, kind='raider')
                         for y in (-50, 50)]
        wingmate = w.resident_fleet[2]
        w.damage_enemy(wingmate)
        self.assertFalse(any(member is wingmate for member in w.enemies))
        self.assertEqual(len(w.resident_fleet), 2)
        w.blast_charges = 1
        w.activate_blast()
        w.update_blast(1.3)
        self.assertEqual(w.enemies, [])
        self.assertEqual(w.score, 1000)


if __name__ == '__main__':
    unittest.main()
