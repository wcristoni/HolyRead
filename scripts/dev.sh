#!/usr/bin/env bash
# HolyRead — local dev launcher with LAN QR code.
# Starts backend (FastAPI, :8000) + frontend (static, :8080) bound to 0.0.0.0.
# Prints a QR code in the terminal pointing to the frontend at your LAN IP, so
# you can open the app on your phone (same WiFi).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACK="$ROOT/backend"
FRONT="$ROOT/frontend"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-8080}"

# Detect LAN IP (macOS first, then Linux fallback).
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
[[ -z "$LAN_IP" ]] && LAN_IP="$(ipconfig getifaddr en1 2>/dev/null || true)"
[[ -z "$LAN_IP" ]] && LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
[[ -z "$LAN_IP" ]] && LAN_IP="127.0.0.1"

FRONTEND_URL="http://${LAN_IP}:${FRONTEND_PORT}"
BACKEND_URL="http://${LAN_IP}:${BACKEND_PORT}"

# CORS allowlist — allow all common dev origins
export ALLOWED_ORIGINS="http://localhost:${FRONTEND_PORT},http://127.0.0.1:${FRONTEND_PORT},${FRONTEND_URL}"
export PORT="$BACKEND_PORT"
export HOST="0.0.0.0"

# venv + deps
if [[ ! -d "$BACK/.venv" ]]; then
  echo "→ creating backend venv…"
  python3 -m venv "$BACK/.venv"
fi
"$BACK/.venv/bin/pip" install --quiet --disable-pip-version-check -e "$BACK"
"$BACK/.venv/bin/pip" install --quiet --disable-pip-version-check qrcode

cleanup() {
  jobs -p | xargs -I{} kill {} 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM EXIT

# Start backend
echo "→ backend  : $BACKEND_URL"
"$BACK/.venv/bin/uvicorn" app.main:app \
  --app-dir "$BACK" \
  --host "$HOST" --port "$BACKEND_PORT" \
  --log-level warning &

# Start frontend (static)
echo "→ frontend : $FRONTEND_URL"
python3 -m http.server -d "$FRONT" "$FRONTEND_PORT" --bind 0.0.0.0 \
  >/tmp/holyread-front.log 2>&1 &

sleep 2

# Health probe
if ! curl -fsS "http://127.0.0.1:${BACKEND_PORT}/healthz" >/dev/null; then
  echo "✗ backend não respondeu em /healthz — abortando"
  exit 1
fi

cat <<EOF

─────────────────────────────────────────────
 HolyRead — Dev local
─────────────────────────────────────────────
 Frontend  : $FRONTEND_URL
 Backend   : $BACKEND_URL
 API docs  : ${BACKEND_URL}/docs

 Aponte o celular pro QR (mesma rede WiFi):
EOF

"$BACK/.venv/bin/python" - <<PY
import qrcode
qr = qrcode.QRCode(border=1)
qr.add_data("$FRONTEND_URL")
qr.make()
qr.print_ascii(invert=True)
PY

echo "─────────────────────────────────────────────"
echo " Ctrl+C para parar."
echo

wait
