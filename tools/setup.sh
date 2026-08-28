#!/usr/bin/env bash
# Prepare a fresh container to build an edition.
#
# Chromium is what shapes the Tamil, so it has to be there. Many images ship
# one already (Playwright's own, or one at PLAYWRIGHT_BROWSERS_PATH); pdf.py
# finds those on its own. Only download one if nothing is present.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "· python dependencies"
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt

if python3 - <<'PY'
import sys
sys.path.insert(0, "src")
from tamilpaper.pdf import _chromium_path
sys.exit(0 if _chromium_path() else 1)
PY
then
  echo "· chromium already present"
else
  echo "· downloading chromium"
  python3 -m playwright install chromium
fi

echo "· checking the build"
python3 build.py --list-presets > /dev/null
echo "ready"
