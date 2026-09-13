#!/usr/bin/env python3
import argparse,json,os,platform,struct,subprocess,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('payload',type=Path);args=p.parse_args()
meta=json.loads((args.payload/'manifest.json').read_text());exe=(args.payload/meta['executable']).resolve()
if not exe.exists():exe=(args.payload/'runtime'/Path(meta['executable']).name).resolve()
with tempfile.TemporaryDirectory(prefix='retro-native-smoke-') as d:
 for game in ('asteroids','pong','snake'):
  output=Path(d)/(game+'.png')
  subprocess.run([str(exe),'--game',game,'--frames',str(output),'--duration','1','--width','640','--height','360'],check=True,timeout=30,env=dict(os.environ,QT_QPA_PLATFORM='offscreen'))
  data=output.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[16:24])==(640,360)
  print(game+': native frame worker OK',flush=True)
