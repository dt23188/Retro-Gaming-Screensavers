from pathlib import Path
import sys, unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from engine import World,Vec,Shot,Saucer,CorePart

class WeaponTests(unittest.TestCase):
    def quiet(self):
        w=World(1979,640,360);w.rocks=[];w.parts=[];w.shots=[]
        w.ship.position=Vec(-250,150);w.ship.velocity=Vec();w.camera=Vec()
        w.autopilot=lambda dt:None;w.choose_powerups=lambda dt:None
        w.stream_timer=100;w.saucer_timer=100
        return w
    def test_missile_clips_through_rock_and_hits_enemy(self):
        w=self.quiet();rock=w.make_rock(Vec(90,0),0,Vec());w.rocks=[rock]
        w.saucer=Saucer(Vec(220,0),Vec(),False,cooldown=100)
        w.shots=[Shot(Vec(),Vec(1000,0),missile=True)]
        w.step(.15)
        self.assertIn(rock,w.rocks)
        self.assertEqual(len(w.shots),1)
        self.assertIsNotNone(w.saucer)
        w.step(.15)
        self.assertIn(rock,w.rocks)
        self.assertIsNone(w.saucer)
        self.assertEqual(w.score,200)
    def test_missiles_are_saved_without_enemy_and_blaster_is_independent(self):
        w=self.quiet();w.missile_ammo=8
        self.assertFalse(w.launch_missile())
        for _ in range(4):w.fire_timer=0;w.fire()
        self.assertEqual(w.missile_ammo,8)
        self.assertTrue(all(not s.missile for s in w.shots))
        w.saucer=Saucer(Vec(120,0),Vec(),False)
        self.assertTrue(w.launch_missile())
        self.assertEqual(len(w.shots),5)
        self.assertEqual(w.missile_ammo,7)
        self.assertFalse(w.launch_missile())
    def test_radial_blast_clears_visible_objects_without_splitting(self):
        w=self.quiet();inside=w.make_rock(Vec(150,0),2,Vec());outside=w.make_rock(Vec(1000,0),2,Vec())
        w.rocks=[inside,outside];w.saucer=Saucer(Vec(200,0),Vec(),False)
        w.blast_charges=1
        self.assertTrue(w.activate_blast())
        self.assertFalse(w.activate_blast())
        w.update_blast(.02)
        self.assertIn(inside,w.rocks)
        w.update_blast(1.3)
        self.assertEqual(w.rocks,[outside]);self.assertIsNone(w.saucer)
        self.assertEqual(w.blast_charges,0)
        self.assertGreater(w.blast.radius,0)
    def test_each_enemy_drop_type_and_no_drop_branch(self):
        w=self.quiet()
        for kind in ('missile','shield','blast','core'):
            w.saucer=Saucer(Vec(100,0),Vec(),False)
            with patch.object(w.rng,'random',return_value=0),patch.object(w.rng,'choices',return_value=[kind]):w.destroy_enemy()
            self.assertEqual(w.parts[-1].kind,kind)
            self.assertEqual(w.parts[-1].position,Vec(100,0))
        count=len(w.parts);w.saucer=Saucer(Vec(100,0),Vec(),False)
        with patch.object(w.rng,'random',return_value=.9):w.destroy_enemy()
        self.assertEqual(len(w.parts),count)
    def test_autopilot_uses_blast_for_surrounding_rocks(self):
        w=World(1979);w.blast_charges=1
        w.rocks=[w.make_rock(Vec(x,y),0,Vec()) for x,y in [(70,0),(-70,0),(0,70)]]
        w.choose_powerups(.1)
        self.assertEqual(w.blast_charges,0)
        self.assertIsNotNone(w.blast)

    def test_autopilot_saves_shield_then_uses_it_when_threatened(self):
        w=World(1979);w.rocks=[];w.parts=[CorePart(Vec(),kind='shield')]
        w.collect_parts(1/120);w.choose_powerups(.1)
        self.assertEqual(w.shield_charges,1);self.assertEqual(w.shield_remaining,0)
        w.rocks=[w.make_rock(Vec(60,0),0,Vec())];w.choose_powerups(.1)
        self.assertEqual(w.shield_charges,0);self.assertEqual(w.shield_remaining,25)

if __name__=='__main__':unittest.main()
