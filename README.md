# Hy-MT2-30B-A3B Q4_K_M — DGX Spark Optimized Recipe 🌐

**Production-grade `llama-server` recipe for Hy-MT2-30B-A3B on NVIDIA DGX Spark / GB10**, optimized for Chinese↔Vietnamese neural machine translation with continuous batching and tuned parallel processing.

> 📊 **30B MoE parameters, ~3B active** — runs at ~3.7 chunks/min with parallel=6, alongside Qwen35 on same hardware.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hardware: DGX Spark](https://img.shields.io/badge/Hardware-DGX%20Spark%20%2F%20GB10-76B900?logo=nvidia)](https://www.nvidia.com/en-us/products/workstations/dgx-spark/)
[![Model: Hy-MT2](https://img.shields.io/badge/Model-Hy--MT2--30B--A3B-green)](https://huggingface.co/)

---

## Model Overview

| Property | Value |
|---|---|
| **Model** | Hy-MT2-30B-A3B |
| **Architecture** | Mixture-of-Experts (MoE) — hy_v3 |
| **Total params** | 30B |
| **Active params** | ~3B per token |
| **Quantization** | Q4_K_M (~18.2 GB on disk) |
| **Task** | Chinese ↔ Vietnamese machine translation |
| **Context window** | 96K tokens |
| **llama.cpp** | Patched build for hy_v3 support |

## What Makes This Recipe Different

| Feature | Why |
|---|---|
| `--parallel 6 --cont-batching` | Translation-optimized: process 6 chunks simultaneously |
| `--ubatch-size 4096` | Tuned for translation batch sizes — 3.72 chunks/min |
| `--no-mmap --mlock` | Critical on GB10 unified memory |
| `--cache-type-k/v q8_0` | 2x VRAM savings for KV cache |
| `--cache-reuse 256` | Reuse KV prefix for repeated translation patterns |
| `--flash-attn on` | Blackwell SM121 native support |
| Systemd auto-start | Survive reboots without manual intervention |

## Quick Start

### Prerequisites

- **NVIDIA DGX Spark / GB10** (128GB unified memory)
- **Patched llama.cpp** built with CUDA + hy_v3 architecture support
- **~19 GB disk** for model file
- `bash`, `curl`

### 1. Download Model

```bash
# Download Hy-MT2-30B-A3B Q4_K_M GGUF
huggingface-cli download <repo>/Hy-MT2-30B-A3B-GGUF \
  Hy-MT2-30B-A3B-Q4_K_M.gguf \
  --local-dir .
```

### 2. Configure `start.sh`

```bash
MODEL="/path/to/Hy-MT2-30B-A3B-Q4_K_M.gguf"
PATCHED_LLAMA="/path/to/patched-llama-server"  # hy_v3 build
PORT="${PORT:-8002}"
```

### 3. Start

```bash
chmod +x start.sh stop.sh
./start.sh
# ✅ Hy-MT2-30B-A3B ready on http://127.0.0.1:8002/v1
```

### 4. Translate

```bash
curl http://127.0.0.1:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Translate to Vietnamese: 人工智能正在改变世界。"}],
    "max_tokens": 200,
    "temperature": 0.3,
    "stream": false
  }' | jq '.choices[0].message.content'
```

### 5. Stop

```bash
./stop.sh
```

## Server Flags Explained

| Flag | Value | Why |
|---|---|---|
| `--parallel` | `6` | Process 6 translation chunks simultaneously |
| `--cont-batching` | — | Continuous batching for throughput |
| `--ubatch-size` | `4096` | Large batches optimal for translation (3.72 chunks/min) |
| `--no-mmap` | — | **Critical** — mmap slowdown on GB10 unified memory |
| `--mlock` | — | Prevent model pages from swap |
| `--cache-type-k/v` | `q8_0` | 2x VRAM savings (96K ctx) |
| `--cache-reuse` | `256` | Prefix reuse for repeated translation patterns |
| `--ctx-size` | `98304` | 96K context — enough for long documents |
| `-ngl` | `99` | Full GPU offload |
| `--flash-attn` | `on` | Blackwell SM121 native |

### What's NOT included (vs Qwen35 recipe)

| Feature | Why not |
|---|---|
| MTP drafter | Hy-MT2 architecture doesn't support speculative decoding |
| Vision (mmproj) | Translation-only model, no multimodal |
| Thinking/CoT | Not applicable for NMT |
| `--spec-draft-model` | No MTP heads in hy_v3 architecture |

## Running Alongside Qwen35 on GB10

Both models fit comfortably on a single DGX Spark:

| Model | VRAM | Port |
|---|---|---|
| Hy-MT2 Q4_K_M | ~23 GB | `:8002` |
| Qwen35 Q8_K_XL | ~45 GB | `:8000` |
| **Total** | **~68 GB** | |
| **Free** | **~60 GB** | |

> See [Qwen3.6-35B-A3B DGX Spark Optimized Recipe](https://github.com/binhdnguyen/Qwen3.6-35B-A3B-UD-Q8_K_XL-DGX-Spark-Optimized) for the companion Qwen35 setup.

## Auto-start on Boot (systemd)

```bash
mkdir -p ~/.config/systemd/user/
cp systemd/llama-hymt2.service ~/.config/systemd/user/
sudo loginctl enable-linger $USER
systemctl --user daemon-reload
systemctl --user enable --now llama-hymt2.service
```

## Building the Patched llama.cpp

Hy-MT2 uses a custom `hy_v3` architecture requiring a patched llama.cpp build:

```bash
git clone <hy-mt2-llama.cpp-repo>
cd llama.cpp

cmake -B build-hyv3-cuda \
  -DGGML_CUDA=ON \
  -DGGML_CUDA_FA_ALL_QUANTS=ON \
  -DCMAKE_CUDA_ARCHITECTURES=121 \
  -DGGML_NATIVE=ON

cmake --build build-hyv3-cuda --config Release -j 20
```

> The patched binary lives at `build-hyv3-cuda/bin/llama-server` — separate from the main llama.cpp build.

## VRAM Budget

| Component | Size |
|---|---|
| Q4_K_M model (18.2 GB) | ~18.5 GB |
| KV cache 96K ctx (q8_0) | ~1.5 GB |
| Parallel=6 overhead | ~3 GB |
| CUDA overhead | ~0.5 GB |
| **Total** | **~23 GB** |

> Leaves ~105 GB free on 128GB DGX Spark — Qwen35 Q8_K_XL fits alongside.

## Benchmarks

*Speed tests coming after translation batch.* Stay tuned.

## Related Projects

- [Qwen3.6-35B-A3B DGX Spark Optimized](https://github.com/binhdnguyen/Qwen3.6-35B-A3B-UD-Q8_K_XL-DGX-Spark-Optimized) — companion recipe
- [llama.cpp Discussion #21112](https://github.com/ggml-org/llama.cpp/discussions/21112) — optimization guidance
- [TransLLM](https://github.com/) — Chinese-Vietnamese translation pipeline using this model

## License

MIT — see [LICENSE](LICENSE).

---

Made with ❤️ for the NMT + local LLM community.
