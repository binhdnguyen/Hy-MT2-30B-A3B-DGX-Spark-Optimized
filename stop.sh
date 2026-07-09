#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.llama-hymt2.pid"
PORT="${PORT:-8002}"

if [[ -f "$PID_FILE" ]]; then
  pid=$(cat "$PID_FILE")
  if kill -0 "$pid" 2>/dev/null; then
    echo "Stopping Hy-MT2 (pid $pid)..."
    kill "$pid"
    for i in $(seq 1 15); do
      if ! kill -0 "$pid" 2>/dev/null; then
        echo "✅ Stopped"
        rm -f "$PID_FILE"
        exit 0
      fi
      sleep 1
    done
    echo "Force killing..."
    kill -9 "$pid" 2>/dev/null || true
    rm -f "$PID_FILE"
    echo "✅ Force stopped"
    exit 0
  fi
  rm -f "$PID_FILE"
  echo "PID file stale — removed"
fi

# Fallback: find by port
pids=$(pgrep -f "llama-server.*--port $PORT" 2>/dev/null || true)
if [[ -n "$pids" ]]; then
  echo "Found Hy-MT2 on port $PORT: $pids"
  kill $pids 2>/dev/null || true
  echo "✅ Stopped"
  exit 0
fi

echo "No running Hy-MT2 found"
