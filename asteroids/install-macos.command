#!/bin/bash
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
game='asteroids'
[[ $(uname -s) == Darwin ]] || { echo 'Run this installer on macOS.' >&2;exit 1; }
offline=false
source_only=false
while (($#));do
 case "$1" in
 --offline) offline=true;;
 --source) source_only=true;;
 --help|-h) echo 'Usage: install-macos.command [--offline] [--source]';exit 0;;
 *) echo "Unknown option: $1" >&2;exit 2;;
 esac
 shift
done
arch=$(uname -m)
install_dir="$HOME/Library/Application Support/RetroGamingScreensavers/$game"
payload=""
for location in "$project_dir/runtimes/macos-$arch" "$project_dir/../runtimes/macos-$arch";do
 [[ ! -f $location/manifest.json ]] || { payload=$location;break; }
done
if [[ -n $payload && $source_only == false ]];then
 (cd "$payload" && shasum -a256 --check SHA256SUMS >/dev/null)
 mkdir -p "$install_dir/runtime" "$HOME/Library/Screen Savers"
 cp -R "$payload/RetroScreensaver/." "$install_dir/runtime/"
 for original in "$payload/native/"*.saver;do
  name=$(basename "$original" .saver)
  case "$game:$name" in asteroids:RetroAsteroids|pong:RetroPong|snake:RetroSnake)
   bundle="$HOME/Library/Screen Savers/$name.saver"
   mkdir -p "$bundle";cp -R "$original/." "$bundle/"
   /usr/bin/plutil -replace WorkerExecutable -string "$install_dir/runtime/RetroScreensaver" "$bundle/Contents/Info.plist"
   /usr/bin/plutil -replace WorkerArguments -json "[\"--game\",\"$game\"]" "$bundle/Contents/Info.plist"
   /usr/bin/codesign --force --sign - "$bundle"
   echo "Installed bundled native screensaver: $bundle (no Homebrew, Python or compiler needed)"
   open 'x-apple.systempreferences:com.apple.ScreenSaver-Settings.extension'
   exit 0;;
  esac
done
 echo 'Matching native .saver bundle is missing.' >&2;exit 1
fi
if [[ $offline == true ]];then echo 'No matching bundled macOS runtime. Build a native release on this architecture first; see PORTABLE.md.' >&2;exit 1;fi
xcrun --find clang >/dev/null 2>&1 || { echo 'Run xcode-select --install, finish installation, then run again.' >&2;exit 1; }
command -v brew >/dev/null || { echo 'Install Homebrew from https://brew.sh first, then run again.' >&2;exit 1; }
brew install python@3.13
python_exe="$(brew --prefix python@3.13)/bin/python3.13"
install_dir="$HOME/Library/Application Support/RetroGamingScreensavers/$game"
mkdir -p "$install_dir"
"$python_exe" -m venv "$install_dir/venv"
"$install_dir/venv/bin/python" -m pip install -r "$project_dir/requirements-portable.txt"
cp -R "$project_dir/src" "$install_dir/"
cp "$project_dir/game.json" "$install_dir/"
if [[ $game == pong ]];then
 brew install cmake
 cmake -S "$project_dir" -B "$install_dir/build" -DCMAKE_BUILD_TYPE=Release
 cmake --build "$install_dir/build" --parallel 2
 install -m755 "$install_dir/build/pong" "$install_dir/pong"
fi
name=$("$python_exe" -c 'import sys;print("Retro"+sys.argv[1].title())' "$game")
bundle="$HOME/Library/Screen Savers/$name.saver"
mkdir -p "$bundle/Contents/MacOS" "$bundle/Contents/Resources"
xcrun clang -DRETRO_CLASS="${name}Saver" -fobjc-arc -bundle -framework Cocoa -framework ScreenSaver "$project_dir/platforms/macos/RetroSaver.m" -o "$bundle/Contents/MacOS/RetroSaver"
"$python_exe" - "$bundle" "$install_dir" "$name" "$game" <<'PY'
from pathlib import Path
import plistlib,sys
bundle,root=map(Path,sys.argv[1:3]);name,game=sys.argv[3:]
info={'CFBundleIdentifier':'local.retro.screensavers.'+game,'CFBundleName':name,'CFBundleExecutable':'RetroSaver','CFBundlePackageType':'BNDL','CFBundleVersion':'1','CFBundleShortVersionString':'1.0','NSPrincipalClass':name+'Saver','WorkerExecutable':str(root/'venv/bin/python'),'WorkerArguments':[str(root/'src/retro_portable.py')]}
(bundle/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
launcher=root/(name+'.command');import shlex
launcher.write_text('#!/bin/sh\nexec '+shlex.quote(str(root/'venv/bin/python'))+' '+shlex.quote(str(root/'src/retro_portable.py'))+' "$@"\n');launcher.chmod(0o755)
PY
codesign --force --sign - "$bundle"
echo "Installed: $bundle"
echo 'Choose it in System Settings > Screen Saver. Keep the Application Support runtime installed.'
open 'x-apple.systempreferences:com.apple.ScreenSaver-Settings.extension'
