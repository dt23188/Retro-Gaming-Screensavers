#!/usr/bin/env python3
"""Build one shared native runtime. Run with Python+Qt Essentials+PyInstaller installed."""
import argparse, hashlib, json, os, platform, shutil, subprocess, sys, tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=root/'runtimes');p.add_argument('--pong-binary',type=Path);args=p.parse_args()
label={'Linux':'linux','Darwin':'macos','Windows':'windows'}[platform.system()]
arch={'AMD64':'x86_64','x86_64':'x86_64','arm64':'arm64','aarch64':'arm64'}.get(platform.machine(),platform.machine())
tag=label+'-'+arch
with tempfile.TemporaryDirectory(prefix='retro-runtime-build-') as d:
 work=Path(d);pong=args.pong_binary
 if pong is None:
  subprocess.run(['cmake','-S',str(root/'pong'),'-B',str(work/'pong'),'-DCMAKE_BUILD_TYPE=Release','-DBUILD_SHARED_LIBS=OFF'],check=True)
  subprocess.run(['cmake','--build',str(work/'pong'),'--config','Release','--parallel','2'],check=True)
  pong=work/'pong'/('Release/pong.exe' if label=='windows' else 'pong')
  if not pong.exists():pong=work/'pong'/'pong.exe'
 cmd=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed','--name','RetroScreensaver','--distpath',str(work/'dist'),'--workpath',str(work/'host'),'--specpath',str(work),'--exclude-module','cairo','--exclude-module','gi','--exclude-module','tkinter','--paths',str(root/'asteroids/src'),'--paths',str(root/'snake/src'),'--add-data',str(root/'asteroids/game.json')+os.pathsep+'.','--add-binary',str(pong.resolve())+os.pathsep+'.',str(root/'asteroids/src/retro_portable.py')]
 subprocess.run(cmd,check=True)
 destination=args.output/tag
 if destination.exists():shutil.rmtree(destination)
 destination.mkdir(parents=True)
 shutil.copytree(work/'dist/RetroScreensaver',destination/'RetroScreensaver')
 if label=='windows':shutil.copy(destination/'RetroScreensaver/RetroScreensaver.exe',destination/'RetroScreensaver/RetroScreensaver.scr')
 if label=='macos':
  native=destination/'native';native.mkdir()
  for game in ('asteroids','pong','snake'):
   name='Retro'+game.title();bundle=native/(name+'.saver');(bundle/'Contents/MacOS').mkdir(parents=True)
   subprocess.run(['xcrun','clang','-mmacosx-version-min=13.0','-DRETRO_CLASS='+name+'Saver','-fobjc-arc','-bundle','-framework','Cocoa','-framework','ScreenSaver',str(root/game/'platforms/macos/RetroSaver.m'),'-o',str(bundle/'Contents/MacOS/RetroSaver')],check=True)
   import plistlib
   (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'local.retro.screensavers.'+game,'CFBundleName':name,'CFBundleExecutable':'RetroSaver','CFBundlePackageType':'BNDL','CFBundleVersion':'1','NSPrincipalClass':name+'Saver','WorkerExecutable':'INSTALLER_REPLACES_THIS','WorkerArguments':['--game',game]}))
   subprocess.run(['codesign','--force','--sign','-',str(bundle)],check=True)
 metadata={'os':label,'architecture':arch,'python':platform.python_version(),'qt':'6.11.2','games':['asteroids','pong','snake'],'executable':'RetroScreensaver/RetroScreensaver'+('.exe' if label=='windows' else ''),'build_platform':platform.platform()}
 if label=='linux':metadata['minimum_glibc']=platform.libc_ver()[1]
 (destination/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
 # Ship notices and corresponding game/raylib sources alongside the runtime.
 notices=destination/'NOTICES';notices.mkdir()
 shutil.copytree(root/'packaging/licenses',notices/'upstream',dirs_exist_ok=True)
 shutil.copy(root/'LICENSE',notices/'PROJECT-LICENSE.txt')
 for game in ('asteroids','pong','snake'):shutil.copy(root/game/'THIRD-PARTY.md',notices/(game+'.md'))
 try:
  import importlib.metadata as im
  for distribution in ('PySide6-Essentials','shiboken6','PyInstaller'):
   dist=im.distribution(distribution)
   for f in dist.files or []:
    if 'license' in str(f).lower() or 'copying' in str(f).lower():
     source=Path(dist.locate_file(f))
     if source.is_file():
      target=notices/distribution/Path(str(f)).name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy(source,target)
 except im.PackageNotFoundError:pass
 files=sorted(p for p in destination.rglob('*') if p.is_file())
 (destination/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+str(f.relative_to(destination))+'\n' for f in files))
 print('Runtime ready:',destination)
