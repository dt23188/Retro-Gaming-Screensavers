#!/usr/bin/env python3
"""Create a distributable archive with checksums for exactly its contents."""
from pathlib import Path
import argparse
import hashlib
import zipfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--source-only', action='store_true')
args = parser.parse_args()
output = root / 'releases'
output.mkdir(exist_ok=True)
runtimes = [] if args.source_only else sorted(
    d.name for d in (root / 'runtimes').glob('*') if d.is_dir())
name = 'retro-gaming-screensavers-' + ('-'.join(runtimes) if runtimes else 'source') + '.zip'
excluded = {'__pycache__', '.git', 'releases', 'build', '.venv', 'venv', 'dist'}
checksums = []
with zipfile.ZipFile(output / name, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for file in sorted(root.rglob('*')):
        relative = file.relative_to(root)
        if not file.is_file() or any(part in excluded for part in relative.parts):
            continue
        if relative == Path('SHA256SUMS') or file.name.endswith(('.pyc', '.zip', '.log')):
            continue
        if file.name == 'Test Asteroids Screensaver.desktop':
            continue  # Generated launchers contain paths for the build machine.
        if args.source_only and relative.parts[0] == 'runtimes':
            continue
        archive.write(file, Path(root.name) / relative)
        checksums.append(hashlib.sha256(file.read_bytes()).hexdigest() + '  ' + relative.as_posix())
    archive.writestr(str(Path(root.name) / 'SHA256SUMS'), '\n'.join(checksums) + '\n')
print(output / name)
