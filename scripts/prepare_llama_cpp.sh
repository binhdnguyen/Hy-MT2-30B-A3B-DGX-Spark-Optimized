#!/usr/bin/env bash
set -euo pipefail

LLAMA_CPP_DIR="${1:-llama.cpp}"
CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
LLAMA_CPP_COMMIT="c57607016a1ebdd08d269e3378eee5546fc3bf3a"
UPSTREAM="https://github.com/ggml-org/llama.cpp"
RECIPE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PATCH_FILE="$RECIPE_DIR/patches/llama-cpp-hyv3.patch"
BUILD_DIR="$LLAMA_CPP_DIR/build-hyv3-cuda"

if [[ ! -f "$PATCH_FILE" ]]; then
  echo "ERROR: HYV3 patch not found: $PATCH_FILE" >&2
  exit 1
fi

if [[ ! -d "$LLAMA_CPP_DIR/.git" ]]; then
  git clone "$UPSTREAM" "$LLAMA_CPP_DIR"
elif [[ -n "$(git -C "$LLAMA_CPP_DIR" status --porcelain)" ]]; then
  echo "ERROR: Refusing to modify a dirty llama.cpp checkout: $LLAMA_CPP_DIR" >&2
  exit 1
fi

git -C "$LLAMA_CPP_DIR" fetch --depth=1 origin "$LLAMA_CPP_COMMIT"
git -C "$LLAMA_CPP_DIR" checkout --detach "$LLAMA_CPP_COMMIT"

prove_hyv3_support() {
  grep -Rqs "HYV3ForCausalLM" "$LLAMA_CPP_DIR/conversion" &&
    grep -Rqs "LLM_ARCH_HYV3" "$LLAMA_CPP_DIR/src" &&
    grep -Rqs "llama_model_hyv3" "$LLAMA_CPP_DIR/src"
}

if prove_hyv3_support; then
  echo "HYV3 support already present at pinned commit"
elif git -C "$LLAMA_CPP_DIR" apply --check "$PATCH_FILE"; then
  git -C "$LLAMA_CPP_DIR" apply "$PATCH_FILE"
else
  echo "ERROR: HYV3 patch does not apply to pinned llama.cpp commit" >&2
  exit 1
fi

if ! prove_hyv3_support; then
  echo "ERROR: HYV3 support could not be proven after patching" >&2
  exit 1
fi

cmake -S "$LLAMA_CPP_DIR" -B "$BUILD_DIR" \
  -DGGML_CUDA=ON \
  -DGGML_CUDA_FA_ALL_QUANTS=ON \
  -DCMAKE_CUDA_ARCHITECTURES=121 \
  -DGGML_NATIVE=ON \
  -DCUDAToolkit_ROOT="$CUDA_HOME" \
  -DLLAMA_CURL=OFF
cmake --build "$BUILD_DIR" --config Release -j"$(nproc)" \
  --target llama-server llama-quantize

for binary in llama-server llama-quantize; do
  path="$BUILD_DIR/bin/$binary"
  if [[ ! -x "$path" ]]; then
    echo "ERROR: Expected binary was not built: $path" >&2
    exit 1
  fi
  echo "$path"
done
