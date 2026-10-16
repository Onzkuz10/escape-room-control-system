#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
if ! command -v python3 >/dev/null || ! command -v npm >/dev/null; then
  echo 'Tarvitset Python 3.11+ ja Node.js 20.19+ (tai 22.12+). macOS: brew install python@3.12 node'
  exit 1
fi
python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11 tai uudempi tarvitaan"'
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
npm ci --prefix frontend --no-audit --no-fund
npm run build --prefix frontend
echo 'Valmis. Käynnistä: ./scripts/start.sh'
