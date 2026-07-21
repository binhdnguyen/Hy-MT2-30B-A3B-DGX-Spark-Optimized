# Hy-MT2-30B-A3B Q8_0 - DGX Spark Optimized Recipe

A reproducible `llama-server` recipe matching the verified local Hy-MT2-30B-A3B Q8_0 deployment on NVIDIA DGX Spark / GB10.

## Verified deployment

| Property | Value |
|---|---|
| Base model | [`tencent/Hy-MT2-30B-A3B`](https://huggingface.co/tencent/Hy-MT2-30B-A3B) |
| Related GGUF repository | [`GrahLnn/Hy-MT2-30B-A3B-4bit-GGUF`](https://huggingface.co/GrahLnn/Hy-MT2-30B-A3B-4bit-GGUF), inspected at `4ae7787` |
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

The deployed Q8_0 artifact is **local-only and of unknown provenance**. Inspection of related model repository commit `4ae7787` found only Q2, Q3, and Q4 files. It does not establish a source or generation path for this Q8_0 file. This recipe therefore does not claim that the exact artifact can be downloaded or regenerated.

Identify the deployed local file only by both checksum and size:

```text
f1603f5515a69e4a04b5e989bc7232f71f9120fe7fb980888c0f4b524f38d86a  Hy-MT2-30B-A3B-Q8_0.gguf
31,985,729,632 bytes
```

Back up this local-only artifact separately before any disk wipe, reinstallation, or model-directory cleanup. `backup_model.sh` fails closed unless the destination is a real mount point on a different filesystem from `/`, rejects symlinked or unsafe destinations, verifies the source, copies through a temporary file, and verifies the destination before publishing it:

```bash
./scripts/backup_model.sh /mnt/model-backup
```

Do not remove the verified local copy until provenance is established or a separately verified backup exists.

## Prerequisites

- NVIDIA DGX Spark / GB10 with a working CUDA driver
- `git`, CMake, a C++ compiler, CUDA toolkit, `bash`, and `curl`
- Enough storage for the local Q8_0 backup and llama.cpp build tree

## Build the pinned patched llama.cpp

The preparation script clones upstream llama.cpp, checks out the exact verified commit, applies the included HYV3 patch, proves required HYV3 markers exist, and builds only `llama-server` and `llama-quantize` with CUDA.

```bash
./scripts/prepare_llama_cpp.sh "$HOME/ai/hy-mt2-gguf-repo/llama.cpp"
```

The script refuses to alter a dirty existing checkout and fails closed if the patch cannot be applied and HYV3 support cannot be proven.

## Install the model

```bash
EXPECTED_SHA256="f1603f5515a69e4a04b5e989bc7232f71f9120fe7fb980888c0f4b524f38d86a"
EXPECTED_SIZE="31985729632"
MODEL="$HOME/ai/models/hy-mt2-30b-a3b-q8/Hy-MT2-30B-A3B-Q8_0.gguf"
mkdir -p "$HOME/ai/models/hy-mt2-30b-a3b-q8"
cp Hy-MT2-30B-A3B-Q8_0.gguf \
  "$MODEL"
[[ "$(sha256sum "$MODEL" | awk '{print $1}')" == "$EXPECTED_SHA256" ]] || {
  echo "Model SHA256 mismatch" >&2
  exit 1
}
[[ "$(stat -c %s -- "$MODEL")" == "$EXPECTED_SIZE" ]] || {
  echo "Model size mismatch" >&2
  exit 1
}
```

Restore a separately verified backup with the same automatic checks:

```bash
EXPECTED_SHA256="f1603f5515a69e4a04b5e989bc7232f71f9120fe7fb980888c0f4b524f38d86a"
EXPECTED_SIZE="31985729632"
MODEL="$HOME/ai/models/hy-mt2-30b-a3b-q8/Hy-MT2-30B-A3B-Q8_0.gguf"
mkdir -p "$(dirname "$MODEL")"
cp /mnt/model-backup/Hy-MT2-30B-A3B-Q8_0.gguf "$MODEL"
[[ "$(sha256sum "$MODEL" | awk '{print $1}')" == "$EXPECTED_SHA256" ]] || {
  echo "Restored model SHA256 mismatch" >&2
  exit 1
}
[[ "$(stat -c %s -- "$MODEL")" == "$EXPECTED_SIZE" ]] || {
  echo "Restored model size mismatch" >&2
  exit 1
}
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

The supplied unit uses `%h` paths, waits for `nvidia-smi`, retries without a start limit, and restarts after failures or clean exits. The installer creates the original `.backup` once using an atomic hard-link publication step and never overwrites it on repeated installs.

```bash
./scripts/install_service.sh
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

Restore the saved unit and restart it:

```bash
UNIT_PATH="$HOME/.config/systemd/user/llama-hymt2.service"
BACKUP_PATH="${UNIT_PATH}.backup"
if [[ -f "$BACKUP_PATH" ]]; then
  cp "$BACKUP_PATH" "$UNIT_PATH"
else
  echo "No saved unit backup found at $BACKUP_PATH" >&2
  exit 1
fi
systemctl --user daemon-reload
systemctl --user enable --now llama-hymt2.service
```

If no previous unit existed and you need to uninstall this one:

```bash
systemctl --user disable --now llama-hymt2.service
rm -f "$HOME/.config/systemd/user/llama-hymt2.service"
systemctl --user daemon-reload
```

No service restart or model load is required to validate this repository's static recipe files.

## License

MIT - see [LICENSE](LICENSE).
