#!/usr/bin/env bash
# Option 1: Start RTMP server for DJI Air 3S and run Kavi on the live feed.
# Usage: ./run_dji_live_rtmp.sh [extra args for main.py, e.g. --process-every-n 10]

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Faster Hugging Face download (optional: pip install hf-transfer)
if python3.11 -c "import hf_transfer" 2>/dev/null; then
  export HF_HUB_ENABLE_HF_TRANSFER=1
fi

RTMP_IMAGE="alfg/nginx-rtmp"
RTMP_CONTAINER="kavi-rtmp"
RTMP_PORT="1935"
STREAM_URL_LOCAL="rtmp://localhost:${RTMP_PORT}/stream/dji"

echo "=============================================="
echo "  Kavi – DJI Air 3S live feed (Option 1)"
echo "=============================================="
echo ""

# 1. Ensure Docker RTMP server is running
if ! command -v docker &>/dev/null; then
  echo "Docker is not installed or not in PATH."
  echo "Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
  echo "Or start an RTMP server manually and run:"
  echo "  python3.11 -m Model.main \"${STREAM_URL_LOCAL}\" --live $*"
  exit 1
fi

if ! docker info &>/dev/null; then
  echo "Docker is not running. Start Docker Desktop and try again."
  exit 1
fi

if docker ps -q -f "name=^${RTMP_CONTAINER}$" 2>/dev/null | grep -q .; then
  echo "[OK] RTMP server already running (container: ${RTMP_CONTAINER})"
elif docker ps -aq -f "name=^${RTMP_CONTAINER}$" 2>/dev/null | grep -q .; then
  echo "Starting existing RTMP container..."
  docker start "$RTMP_CONTAINER"
  echo "[OK] RTMP server started"
else
  echo "Pulling RTMP image (one-time)..."
  docker pull "$RTMP_IMAGE"
  echo "Starting RTMP server..."
  docker run -d -p "${RTMP_PORT}:1935" --name "$RTMP_CONTAINER" "$RTMP_IMAGE"
  echo "[OK] RTMP server running on port ${RTMP_PORT}"
fi

echo ""

# 2. Show DJI Fly URL
PC_IP=""
if command -v ipconfig &>/dev/null; then
  PC_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)
fi
if [ -z "$PC_IP" ]; then
  PC_IP="YOUR_PC_IP"
fi

DJI_URL="rtmp://${PC_IP}:${RTMP_PORT}/stream/dji"
echo "In DJI Fly (Transmission → RTMP), use this URL:"
echo ""
echo "  $DJI_URL"
echo ""
echo "Then tap Start to begin streaming. Keep the stream running."
echo ""

# 3. Run Kavi
echo "Starting Kavi on live stream..."
echo "Stream URL: ${STREAM_URL_LOCAL}"
echo "Press Ctrl+C to stop."
echo ""

exec python3.11 -m Model.main "$STREAM_URL_LOCAL" --live "$@"
