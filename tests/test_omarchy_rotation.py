"""Exercise the taskbar's exact dispatcher invocation without opening windows."""
from pathlib import Path
import os,subprocess,tempfile,unittest

class RotationTests(unittest.TestCase):
    def test_taskbar_activations_cycle_three_launchers(self):
        source=Path(__file__).resolve().parents[1]/'packaging/omarchy/retro-screensaver'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);bin=root/'.local/bin';bin.mkdir(parents=True)
            (root/'.config/omarchy').mkdir(parents=True)
            script=source.read_text().replace('$HOME',str(root)).replace('${XDG_RUNTIME_DIR:-/tmp}',str(root))
            dispatcher=bin/'retro-screensaver';dispatcher.write_text(script);dispatcher.chmod(0o755)
            for name,body in {'pgrep':'exit 1','omarchy':'exit 1','omarchy-shell':'echo false',
                              'omarchy-launch-snake-screensaver':'echo snake',
                              'retro-asteroids-screensaver':'echo asteroids',
                              'retro-pong-screensaver':'echo pong'}.items():
                p=bin/name;p.write_text('#!/bin/sh\n'+body+'\n');p.chmod(0o755)
            env=dict(os.environ,PATH=str(bin)+':'+os.environ['PATH'])
            # A single-game default must not override the taskbar rotation.
            subprocess.run([str(dispatcher),'select','classic-snake'],env=env,check=True)
            choices=[subprocess.check_output([str(dispatcher),'rotation','force'],env=env,text=True).strip() for _ in range(6)]
            self.assertEqual(choices,['snake','asteroids','pong']*2)
            subprocess.run([str(dispatcher),'select','rotation'],env=env,check=True)
            self.assertEqual(subprocess.check_output([str(dispatcher),'run','force'],env=env,text=True).strip(),'snake')

if __name__=='__main__':unittest.main()
