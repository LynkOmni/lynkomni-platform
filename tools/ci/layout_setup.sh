#!/usr/bin/env bash
# Sets up the layout check (fonts for every script and the test browser) quickly and reliably (owner, 19 November 2026).
# The first run downloads them from Ubuntu and keeps a copy in the CI cache (~/layout-cache); later runs restore that copy in
# seconds instead of downloading again, which took 1 to 27 minutes per part. Downloads are retried, so a short outage of the
# package servers never fails a check. The browser's system libraries are installed only if the browser cannot start.
set -euo pipefail
CACHE="$HOME/layout-cache"
retry() { for i in 1 2 3 4 5; do "$@" && return 0; echo "retry $i: $*"; sleep 30; done; return 1; }

if [ -d "$CACHE/fonts/noto-core" ] && [ -d "$CACHE/fonts/noto-cjk" ]; then
  sudo mkdir -p /usr/share/fonts/truetype/noto /usr/share/fonts/opentype/noto
  sudo cp -r "$CACHE/fonts/noto-core/." /usr/share/fonts/truetype/noto/
  sudo cp -r "$CACHE/fonts/noto-cjk/." /usr/share/fonts/opentype/noto/
  sudo fc-cache -f >/dev/null
  echo "fonts restored from the cache"
else
  retry sudo apt-get update -q -o Acquire::Retries=5
  retry sudo apt-get install -y -o Acquire::Retries=5 fonts-noto-core fonts-noto-cjk
  mkdir -p "$CACHE/fonts"
  cp -r /usr/share/fonts/truetype/noto "$CACHE/fonts/noto-core"
  cp -r /usr/share/fonts/opentype/noto "$CACHE/fonts/noto-cjk"
fi

retry pip install -q "playwright==${PLAYWRIGHT_VERSION}"
retry python -m playwright install chromium            # kept in ~/.cache/ms-playwright, which the CI cache also restores
if ! python -c "from playwright.sync_api import sync_playwright as s; p = s().start(); p.chromium.launch().close(); p.stop()"; then
  retry sudo env "PATH=$PATH" python -m playwright install-deps chromium
fi
