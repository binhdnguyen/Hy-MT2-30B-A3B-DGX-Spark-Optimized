# Hy-MT2-30B-A3B Q8_0 - DGX Spark Optimized Recipe

A reproducible `llama-server` recipe matching the verified local Hy-MT2-30B-A3B Q8_0 deployment on NVIDIA DGX Spark / GB10.

## Verified deployment

| Property | Value |
|---|---|
| Base model | [`tencent/Hy-MT2-30B-A3B`](https://huggingface.co/tencent/Hy-MT2-30B-A3B) |
| GGUF source repository | [`GrahLnn/Hy-MT2-30B-A3B-4bit-GGUF`](https://huggingface.co/GrahLnn/Hy-MT2-30B-A3B-4bit-GGUF) |
| Deployed quantization | Q8_0 |
| Deployed filename | `Hy-MT2-30B-A3B-Q8_0.gguf` |
| Size | 31,985,729,632 bytes |
| SHA256 | `f1603f5515a69e4a04b5e989bc7232f71f9120fe7fb980888c0f4b524f38d86a` |
| Context | 98,304 tokens |
| Parallel slots | 6 |
| API | `http://127.0.0.1:8002/v1` |
| llama.cpp base | `c57607016a1ebdd08d269e3378eee5546fc3bf3a` plus `patches/llama-cpp-hyv3.patch` |

The service was verified enabled and active, and its `/health` endpoint returned `{"status":"ok"}`. No throughput or memory number is asserted here because this recipe does not include a reproducible benchmark capture.

## Q8_0 artifact provenance

There is currently **no direct public Q8 download artifact** known to match the deployed file. The GGUF source repository publishes a BF16 conversion source and lower-bit derivatives, but does not currently track this exact Q8_0 file. Do not substitute a guessed URL.

Reproduce the route from the advertised BF16 GGUF:

```bash
git lfs install
git clone https://huggingface.co/GrahLnn/Hy-MT2-30B-A3B-4bit-GGUF
cd Hy-MT2-30B-A3B-4bit-GGUF

$HOME/ai/hy-mt2-gguf-repo/llama.cpp/build-hyv3-cuda/bin/llama-quantize \
  Hy-MT2-30B-A3B-BF16.gguf \
  Hy-MT2-30B-A3B-Q8_0.gguf \
  Q8_0

sha256sum Hy-MT2-30B-A3B-Q8_0.gguf
stat --printf='%s bytes\n' Hy-MT2-30B-A3B-Q8_0.gguf
```

Expected deployed checksum and size:

```text
f1603f5515a69e4a04b5e989bc7232f71f9120fe7fb980888c0f4b524f38d86a  Hy-MT2-30B-A3B-Q8_0.gguf
31,985,729,632 bytes
```

Checksum equality depends on the pinned source artifact, exact patched llama.cpp commit, patch, quantization command, and tooling versions. Verify the result before treating a generated file as identical to the deployment.

## Prerequisites

- NVIDIA DGX Spark / GB10 with a working CUDA driver
- `git`, Git LFS, CMake, a C++ compiler, CUDA toolkit, `bash`, and `curl`
- Enough storage for the BF16 source, Q8_0 output, and build tree

## Build the pinned patched llama.cpp

The preparation script clones upstream llama.cpp, checks out the exact verified commit, applies the included HYV3 patch, proves required HYV3 markers exist, and builds only `llama-server` and `llama-quantize` with CUDA.

```bash
./scripts/prepare_llama_cpp.sh "$HOME/ai/hy-mt2-gguf-repo/llama.cpp"
```

The script refuses to alter a dirty existing checkout and fails closed if the patch cannot be applied and HYV3 support cannot be proven.

## Install the model

```bash
mkdir -p "$HOME/ai/models/hy-mt2-30b-a3b-q8"
cp Hy-MT2-30B-A3B-Q8_0.gguf \
  "$HOME/ai/models/hy-mt2-30b-a3b-q8/Hy-MT2-30B-A3B-Q8_0.gguf"
sha256sum "$HOME/ai/models/hy-mt2-30b-a3b-q8/Hy-MT2-30B-A3B-Q8_0.gguf"
```

## Start with the helper

`start.sh` defaults to portable paths under `$HOME/ai` and preserves `MODEL`, `PATCHED_LLAMA`, `HOST`, and `PORT` overrides.

```bash
./start.sh
curl -fsS http://127.0.0.1:8002/health
```

Expected health response:

```json
{"status":"ok"}
```

Stop the helper-managed process with:

```bash
./stop.sh
```

## Install the systemd user service

The supplied unit uses `%h` paths, waits for `nvidia-smi`, retries without a start limit, and restarts after failures or clean exits.

```bash
mkdir -p "$HOME/.config/systemd/user"
cp systemd/llama-hymt2.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now llama-hymt2.service
systemctl --user status llama-hymt2.service
curl -fsS http://127.0.0.1:8002/health
```

For boot-time user services without an interactive login, an administrator may enable lingering:

```bash
sudo loginctl enable-linger "$USER"
```

## Verified server flags

```text
-ngl 99
--no-mmap --mlock
-c 98304
--parallel 6 --cont-batching
-fa on
--ubatch-size 4096
--cache-type-k q8_0 --cache-type-v q8_0
--cache-reuse 256
--temp 0.7
--jinja
--alias Hy-MT2-30B-A3B
--host 127.0.0.1 --port 8002
```

## Restore or roll back

```bash
systemctl --user disable --now llama-hymt2.service
rm "$HOME/.config/systemd/user/llama-hymt2.service"
systemctl --user daemon-reload
```

If replacing an older unit, save it first and restore that backup instead of deleting it:

```bash
cp "$HOME/.config/systemd/user/llama-hymt2.service" \
  "$HOME/.config/systemd/user/llama-hymt2.service.backup"
```

No service restart or model load is required to validate this repository's static recipe files.

## License

MIT - see [LICENSE](LICENSE).
