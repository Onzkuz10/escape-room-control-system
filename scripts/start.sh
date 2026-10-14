#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
if [ ! -x .venv/bin/python ] || [ ! -f frontend/dist/index.html ]; then
  echo 'Asennus tai käyttöliittymän build puuttuu. Suorita ensin ./scripts/setup.sh'
  exit 1
fi
ROOM_PORT="${ESCAPE_PORT:-8000}"
if ! [[ "$ROOM_PORT" =~ ^[0-9]+$ ]] || (( ROOM_PORT < 1024 || ROOM_PORT > 65535 )); then
  echo 'ESCAPE_PORT-arvon pitää olla kokonaisluku 1024–65535.'
  exit 1
fi
echo "Dashboard:       http://localhost:$ROOM_PORT"
echo "Player Display:  http://localhost:$ROOM_PORT/player"
if command -v ipconfig >/dev/null; then
  for DEVICE in en0 en1; do
    ROOM_IP="$(ipconfig getifaddr "$DEVICE" 2>/dev/null || true)"
    if [ -n "$ROOM_IP" ]; then echo "Pelaajien laite:  http://$ROOM_IP:$ROOM_PORT/player ($DEVICE)"; fi
  done
fi
echo 'Pidä tämä terminaali auki. Lopeta Ctrl+C.'
# Exactly one process owns the physical camera and authoritative game state.
exec .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port "$ROOM_PORT" --workers 1
