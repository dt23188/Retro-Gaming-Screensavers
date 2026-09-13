#!/usr/bin/env bash
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
game='asteroids'
install_dir="${XDG_DATA_HOME:-$HOME/.local/share}/retro-gaming-screensavers/$game"
bin_dir="$HOME/.local/bin"
skip_deps=false
offline=false
source_only=false
while (($#)); do
 case "$1" in
 --prefix) install_dir="${2:?Directory required}"; shift 2;;
 --bin-dir) bin_dir="${2:?Directory required}"; shift 2;;
 --skip-deps) skip_deps=true;shift;;
 --offline) offline=true;shift;;
 --source) source_only=true;shift;;
 --help|-h) echo 'Usage: install-ubuntu.sh [--prefix DIR] [--bin-dir DIR] [--skip-deps] [--offline] [--source]';exit;;
 *) echo "Unknown option: $1" >&2;exit 2;;
 esac
done
arch=$(uname -m)
[[ $arch != aarch64 ]] || arch=arm64
payload=""
for location in "$project_dir/runtimes/linux-$arch" "$project_dir/../runtimes/linux-$arch";do
 [[ ! -f $location/manifest.json ]] || { payload=$location; break; }
done
if [[ -n $payload && $source_only == false ]];then
 required=$(sed -nE 's/.*"minimum_glibc": "([^"]+)".*/\1/p' "$payload/manifest.json")
 current=$(getconf GNU_LIBC_VERSION 2>/dev/null | awk '{print $2}' || true)
 if [[ -n $required && -n $current && $(printf '%s\n' "$required" "$current" | sort -V | head -1) == "$required" ]];then
  (cd "$payload" && sha256sum --check --quiet SHA256SUMS)
  "$payload/RetroScreensaver/RetroScreensaver" --game "$game" --help >/dev/null
  mkdir -p "$install_dir/runtime" "$bin_dir"
  install_dir=$(cd "$install_dir" && pwd)
  [[ $install_dir != "$project_dir" ]] || { echo 'Choose a different installation directory.' >&2;exit 1; }
  cp -a "$payload/RetroScreensaver/." "$install_dir/runtime/"
  launcher="$bin_dir/retro-$game-screensaver"
  printf '#!/usr/bin/env bash\nexec %q --game %q "$@"\n' "$install_dir/runtime/RetroScreensaver" "$game" > "$launcher"
  chmod +x "$launcher"
  apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications";mkdir -p "$apps"
  # Desktop Exec quoting, including percent field-code escaping.
  escaped=${launcher//\\/\\\\};escaped=${escaped//\"/\\\"};escaped=${escaped//%/%%}
  printf '[Desktop Entry]\nType=Application\nName=Retro %s Screensaver\nExec="%s" --preview\nTerminal=false\nCategories=Game;\nActions=Fullscreen;\n\n[Desktop Action Fullscreen]\nName=Start Screensaver\nExec="%s"\n' "$game" "$escaped" "$escaped" > "$apps/retro-$game-screensaver.desktop"
  echo "Installed bundled runtime: $launcher (no Python, pip or compiler needed)"
  exit 0
 fi
 echo "Bundled runtime needs glibc $required; this system has ${current:-unknown}." >&2
fi
if [[ $offline == true ]];then
 echo 'No compatible bundled Linux runtime. Build a release on your oldest target Linux, or install from source online. See PORTABLE.md.' >&2
 exit 1
fi
if [[ $skip_deps == false ]]; then
 command -v apt-get >/dev/null || { echo 'Ubuntu/Debian required, or provision dependencies and use --skip-deps.' >&2;exit 1; }
 sudo apt-get update
 packages=(python3 python3-venv libxcb-cursor0 libxkbcommon-x11-0 libegl1)
 if [[ $game == pong ]];then packages+=(build-essential cmake libx11-dev libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev libgl1-mesa-dev);fi
 sudo apt-get install -y "${packages[@]}"
fi
mkdir -p "$install_dir" "$bin_dir"
install_dir=$(cd "$install_dir" && pwd)
[[ "$install_dir" != "$project_dir" ]] || { echo 'Installation must differ from source directory.' >&2;exit 1; }
if [[ ! -x "$install_dir/venv/bin/python" ]]; then python3 -m venv "$install_dir/venv"; fi
if [[ $skip_deps == false ]];then "$install_dir/venv/bin/python" -m pip install -r "$project_dir/requirements-portable.txt";fi
"$install_dir/venv/bin/python" -c 'import PySide6'
cp -R "$project_dir/src" "$install_dir/"
cp "$project_dir/game.json" "$install_dir/"
if [[ $game == pong ]];then
 cmake -S "$project_dir" -B "$install_dir/build" -DCMAKE_BUILD_TYPE=Release
 cmake --build "$install_dir/build" --parallel 2
 install -m755 "$install_dir/build/pong" "$install_dir/pong"
fi
python3 - "$install_dir" "$bin_dir" "$game" <<'PY'
from pathlib import Path
import os,shlex,sys
root,bindir=map(Path,sys.argv[1:3]);game=sys.argv[3]
launcher=bindir/('retro-'+game+'-screensaver')
launcher.write_text('#!/bin/sh\nexec '+shlex.quote(str(root/'venv/bin/python'))+' '+shlex.quote(str(root/'src/retro_portable.py'))+' "$@"\n');launcher.chmod(0o755)
apps=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'applications';apps.mkdir(parents=True,exist_ok=True)
escaped=str(launcher).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')
(apps/('retro-'+game+'-screensaver.desktop')).write_text('[Desktop Entry]\nType=Application\nName=Retro '+game.title()+' Screensaver\nExec="'+escaped+'" --preview\nTerminal=false\nCategories=Game;\nActions=Fullscreen;\n\n[Desktop Action Fullscreen]\nName=Start Screensaver\nExec="'+escaped+'"\n')
PY
echo "Installed: $bin_dir/retro-$game-screensaver"
echo 'See PORTABLE.md for idle activation on your desktop. Your current screen locker and selection are unchanged.'
