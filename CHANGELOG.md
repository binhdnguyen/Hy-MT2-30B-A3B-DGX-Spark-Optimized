# Changelog

## [1.0.0] - 2026-07-09

### Added
- `start.sh` — production-grade start script with health-check spinner, duplicate guard, PID management
- `stop.sh` — graceful shutdown with fallback to port-based detection
- `--parallel 6 --cont-batching` for translation throughput (3.72 chunks/min)
- `--no-mmap --mlock` for DGX Spark / GB10 unified memory
- `--cache-type-k/v q8_0` for 2x VRAM savings
- `--cache-reuse 256` for translation pattern reuse
- `--ubatch-size 4096` tuned for translation batch sizes
- `--flash-attn on` for Blackwell SM121
- systemd user service for auto-start on boot (see `systemd/`)
- `.gitignore` — excludes logs, PID files, and downloaded model weights
- Runs alongside Qwen35 Q8_K_XL on same GB10 (68 GB total / 128 GB)

### Notes
- No MTP support — Hy-MT2 hy_v3 architecture doesn't support speculative decoding
- Speed benchmarks pending (after translation batch completes)
- Built against patched llama.cpp with hy_v3 architecture support
