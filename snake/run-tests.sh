#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
export QT_QPA_PLATFORM=offscreen
"${PYTHON:-python3}" -m unittest discover -s tests -p 'test_*.py'
