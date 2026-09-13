from pathlib import Path
import sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'asteroids/src'))
import retro_portable as host

class PongMonitorTests(unittest.TestCase):
    def test_distinct_complementary_team_pairs(self):
        for count in (1,2,3,6):
            hues=host.monitor_team_hues(count)
            self.assertEqual(len(hues),count)
            self.assertTrue(all(0 <= hue < 180 for hue in hues))
            self.assertEqual(len(set(round(hue,6) for hue in hues)),count)
            if count>1:
                ordered=sorted(hues)
                gaps=[(ordered[(i+1)%count]-ordered[i])%180 for i in range(count)]
                for gap in gaps:self.assertAlmostEqual(gap,180/count)

    def test_each_match_has_its_own_worker_frame_and_palette(self):
        with patch.object(host,'GAME','pong'),patch.object(host.subprocess,'Popen') as popen:
            first=host.Simulation(640,360,team_hue=20)
            second=host.Simulation(800,600,team_hue=110)
            try:
                self.assertNotEqual(first.frame,second.frame)
                self.assertEqual(popen.call_count,2)
                commands=[c.args[0] for c in popen.call_args_list]
                self.assertEqual(commands[0][-2:],['--team-hue','20'])
                self.assertEqual(commands[1][-2:],['--team-hue','110'])
                self.assertIn('800',commands[1])
            finally:first.close();second.close()

if __name__=='__main__':unittest.main()
