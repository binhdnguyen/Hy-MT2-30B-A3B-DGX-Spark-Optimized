#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Hy-MT2-30B-A3B Q4_K_M — Translation Server — DGX Spark / GB10
# Optimized: parallel 6, cont-batching, ubatch 4096, mlock, cache-reuse
# ============================================================================

MODEL="${MODEL:-/path/to/Hy-MT2-30B-A3B-Q4_K_M.gguf}"
PATCHED_LLAMA="${PATCHED_LLAMA:-/path/to/patched-llama-server}"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8002}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.llama-hymt2.pid"
LOG_FILE="$SCRIPT_DIR/.llama-hymt2.log"
READY_URL="http://127.0.0.1:${PORT}/health"

# ---- Validate ----
if [[ ! -f "$MODEL" ]]; then
  echo "ERROR: Model not found at $MODEL" >&2
  echo "Set MODEL=/path/to/Hy-MT2-30B-A3B-Q4_K_M.gguf" >&2
  exit 1
fi
if [[ ! -x "$PATCHED_LLAMA" ]]; then
  echo "ERROR: Patched llama-server not found at $PATCHED_LLAMA" >&2
  echo "Set PATCHED_LLAMA=/path/to/llama-server (hy_v3 build)" >&2
  exit 1
fi

# ---- Check if already running ----
if [[ -f "$PID_FILE" ]]; then
  pid=$(cat "$PID_FILE")
  if kill -0 "$pid" 2>/dev/null && curl -fsS "$READY_URL" >/dev/null 2>&1; then
    echo "Hy-MT2 already running (pid $pid) on $HOST:$PORT"
    exit 0
  fi
  echo "Stale PID — cleaning up"
  rm -f "$PID_FILE"
fi

echo "Starting Hy-MT2-30B-A3B on $HOST:$PORT"
echo "Model:  $(basename "$MODEL")"
echo "Log:    $LOG_FILE"

nohup "$PATCHED_LLAMA" \
  -m "$MODEL" \
  -ngl 99 \
  --no-mmap \
  --mlock \
  -c 98304 \
  --parallel 6 \
  --cont-batching \
  -fa on \
  --ubatch-size 4096 \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --cache-reuse 256 \
  --jinja \
  --alias "Hy-MT2-30B-A3B" \
  --host "$HOST" \
  --port "$PORT" \
  >"$LOG_FILE" 2>&1 &

server_pid=$!
echo "$server_pid" > "$PID_FILE"
echo "PID: $server_pid"
echo "Waiting for server to become ready..."

spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
i=0 elapsed=0
while ! curl -fsS "$READY_URL" >/dev/null 2>&1; do
  if ! kill -0 "$server_pid" 2>/dev/null; then
    echo ""
    echo "ERROR: Hy-MT2 exited before becoming ready"
    tail -30 "$LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
  fi
  printf '\r\033[K%s %02d:%02d' "${spin:$((i % ${#spin})):1}" $((elapsed / 60)) $((elapsed % 60))
  sleep 2
  i=$((i + 1))
  elapsed=$((elapsed + 2))
done

printf '\r\033[K'
echo "✅ Hy-MT2-30B-A3B ready on http://${HOST}:${PORT}/v1 (${elapsed}s)"
