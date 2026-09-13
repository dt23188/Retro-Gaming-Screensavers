from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from engine import World, Vec, Shot, Saucer

class EffectTests(unittest.TestCase):
    def quiet(self):
        w=World(42);w.rocks=[];w.parts=[];w.saucer_timer=999;w.stream_timer=999
        w.ship.velocity=Vec();w.autopilot=lambda dt:None;w.choose_powerups=lambda dt:None
        return w

    def test_flash_only_on_successful_fire_and_fades(self):
        w=self.quiet();w.fire();self.assertGreater(w.ship.muzzle_flash,0)
        w.step(.04);remaining=w.ship.muzzle_flash
        w.fire();self.assertEqual(w.ship.muzzle_flash,remaining)
        w.step(.1);self.assertEqual(w.ship.muzzle_flash,0)
        w.saucer=Saucer(Vec(300,0),Vec(),False,cooldown=0)
        w.update_saucer(.01)
        self.assertGreater(w.saucer.muzzle_flash,0)
        w.update_saucer(.1);self.assertEqual(w.saucer.muzzle_flash,0)

    def test_blaster_hit_on_protected_ship_still_sparks(self):
        w=self.quiet();w.shots=[Shot(Vec(-30,0),Vec(1000,0),hostile=True)]
        w.step(.03)
        self.assertFalse(w.dead)
        self.assertTrue(any(s.kind=='impact_boom' for s in w.sparks))
        w.step(.4)
        self.assertFalse(any(s.kind.startswith('impact') for s in w.sparks))

    def test_impact_at_contact_does_not_change_gameplay_rng(self):
        w=self.quiet();state=w.rng.getstate()
        w.blaster_impact(Shot(Vec(100,0),Vec(100,0),previous=Vec()),.3)
        self.assertEqual(w.rng.getstate(),state)
        self.assertEqual(w.sparks[0].position,Vec(30,0))
        self.assertEqual(sum(s.kind=='impact' for s in w.sparks),14)

if __name__=='__main__':unittest.main()
