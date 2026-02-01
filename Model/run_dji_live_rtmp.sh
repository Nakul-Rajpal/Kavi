#!/usr/bin/env bash
# Start RTMP server for DJI Air 3S so the live video shows in the Kavi UI (Live tab).
# By default this only starts the server; no model processing.
#
# Usage:
#   ./run_dji_live_rtmp.sh              # Video only: start server, show instructions
#   ./run_dji_live_rtmp.sh --with-detection [args]  # Also run SAM3 detection on the stream

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

RUN_DETECTION=false
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-detection)
      RUN_DETECTION=true
      shift
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

RTMP_IMAGE="alfg/nginx-rtmp"
RTMP_CONTAINER="kavi-rtmp"
RTMP_PORT="1935"
HLS_HTTP_PORT="8080"
# Simple config: app "live", stream key = last path segment -> HLS at /live/STREAM_KEY/index.m3u8
# Kavi UI expects stream key "djidji" by default (or set LIVE_STREAM_KEY); use same key in DJI Fly URL.
NGINX_CONF="${SCRIPT_DIR}/nginx-rtmp-simple.conf"
STREAM_KEY="${LIVE_STREAM_KEY:-djidji}"
STREAM_URL_LOCAL="rtmp://localhost:${RTMP_PORT}/live/${STREAM_KEY}"
HLS_STREAM_URL="http://localhost:${HLS_HTTP_PORT}/live/${STREAM_KEY}/index.m3u8"

echo "=============================================="
echo "  Kavi – DJI Air 3S live video (UI only)"
echo "=============================================="
echo ""

# 1. Ensure Docker RTMP server is running
if ! command -v docker &>/dev/null; then
  echo "Docker is not installed or not in PATH."
  echo "Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
  exit 1
fi

if ! docker info &>/dev/null; then
  echo "Docker is not running. Start Docker Desktop and try again."
  exit 1
fi

# Use simple config (no FFmpeg exec) so HLS works reliably; recreate so our config is always used
if [ ! -f "$NGINX_CONF" ]; then
  echo "Error: Config not found: $NGINX_CONF"
  exit 1
fi

docker rm -f "$RTMP_CONTAINER" 2>/dev/null || true
if ! docker image inspect "$RTMP_IMAGE" >/dev/null 2>&1; then
  echo "Pulling RTMP image (one-time)..."
  docker pull "$RTMP_IMAGE"
fi
echo "Starting RTMP server (simple HLS, no FFmpeg exec)..."
docker run -d -p "${RTMP_PORT}:1935" -p "${HLS_HTTP_PORT}:80" \
  -v "${NGINX_CONF}:/etc/nginx/nginx.conf.template:ro" \
  --name "$RTMP_CONTAINER" "$RTMP_IMAGE"
echo "[OK] RTMP server running: port ${RTMP_PORT} (ingest), port ${HLS_HTTP_PORT} (HLS)"

echo ""

# 2. Show DJI Fly URL and UI instructions
PC_IP=""
if command -v ipconfig &>/dev/null; then
  PC_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)
fi
if [ -z "$PC_IP" ]; then
  PC_IP="YOUR_PC_IP"
fi

DJI_URL="rtmp://${PC_IP}:${RTMP_PORT}/live/${STREAM_KEY}"
echo "1. In DJI Fly (Transmission → RTMP), set URL and tap Start:"
echo "   $DJI_URL"
echo "   (Stream key must match; Kavi Live tab uses \"${STREAM_KEY}\" by default.)"
echo ""
echo "2. On this Mac, start the Kavi UI and open the Live tab:"
echo "   npm run dev"
echo "   Then open http://localhost:3000 and click 'Live' in the header."
echo ""
echo "   The video will show in the Live tab while DJI Fly is streaming."
echo ""

if [ "$RUN_DETECTION" = true ]; then
  if python3.11 -c "import hf_transfer" 2>/dev/null; then
    export HF_HUB_ENABLE_HF_TRANSFER=1
  fi
  echo "3. Starting Kavi detection on live stream (Ctrl+C to stop)..."
  echo ""
  exec python3.11 -m Model.main "$STREAM_URL_LOCAL" --live "${EXTRA_ARGS[@]}"
else
  echo "Model processing is disabled. To run detection on the stream, use:"
  echo "   ./Model/run_dji_live_rtmp.sh --with-detection"
  echo ""
  echo "Server is running. Press Ctrl+C when you're done."
  exec tail -f /dev/null
fi
