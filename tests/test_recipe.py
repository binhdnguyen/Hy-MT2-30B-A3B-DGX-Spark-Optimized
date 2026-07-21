from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
LIVE_FLAGS = [
    "-ngl 99",
    "--no-mmap",
    "--mlock",
    "-c 98304",
    "--parallel 6",
    "--cont-batching",
    "-fa on",
    "--ubatch-size 4096",
    "--cache-type-k q8_0",
    "--cache-type-v q8_0",
    "--cache-reuse 256",
    "--temp 0.7",
    "--jinja",
    "--alias Hy-MT2-30B-A3B",
]


class RecipeTests(unittest.TestCase):
    def text(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_start_defaults_to_portable_live_q8_paths_and_flags(self):
        text = self.text("start.sh")
        self.assertIn(
            'MODEL="${MODEL:-$HOME/ai/models/hy-mt2-30b-a3b-q8/'
            'Hy-MT2-30B-A3B-Q8_0.gguf}"',
            text,
        )
        self.assertIn(
            'PATCHED_LLAMA="${PATCHED_LLAMA:-$HOME/ai/hy-mt2-gguf-repo/'
            'llama.cpp/build-hyv3-cuda/bin/llama-server}"',
            text,
        )
        for flag in LIVE_FLAGS:
            self.assertIn(flag, text)
        self.assertIn('--host "$HOST"', text)
        self.assertIn('--port "$PORT"', text)
        self.assertNotRegex(text, r"/path/to|Q4_K_M|[✅⠋]")

    def test_start_keeps_pid_and_readiness_safety(self):
        text = self.text("start.sh")
        self.assertIn("kill -0", text)
        self.assertIn("/health", text)
        self.assertIn('rm -f "$PID_FILE"', text)

    def test_systemd_matches_portable_live_policy(self):
        text = self.text("systemd/llama-hymt2.service")
        self.assertIn("Description=Hy-MT2-30B-A3B Q8_0", text)
        self.assertIn("StartLimitIntervalSec=0", text)
        self.assertIn("nvidia-smi -L", text)
        self.assertIn("ExecStart=%h/ai/hy-mt2-gguf-repo/", text)
        self.assertIn(
            "-m %h/ai/models/hy-mt2-30b-a3b-q8/"
            "Hy-MT2-30B-A3B-Q8_0.gguf",
            text,
        )
        for flag in LIVE_FLAGS:
            self.assertIn(flag, text)
        self.assertIn("--host 127.0.0.1", text)
        self.assertIn("--port 8002", text)
        self.assertIn("Restart=always", text)
        self.assertIn("RestartSec=15", text)
        self.assertIn("TimeoutStartSec=300", text)
        self.assertIn("TimeoutStopSec=30", text)
        self.assertNotRegex(text, r"/path/to|Q4_K_M")

    def test_prepare_script_pins_commit_and_fails_closed(self):
        text = self.text("scripts/prepare_llama_cpp.sh")
        self.assertIn(
            'LLAMA_CPP_COMMIT="c57607016a1ebdd08d269e3378eee5546fc3bf3a"',
            text,
        )
        self.assertIn("git -C", text)
        self.assertIn('checkout --detach "$LLAMA_CPP_COMMIT"', text)
        self.assertIn("apply --check", text)
        self.assertIn("HYV3ForCausalLM", text)
        self.assertIn("LLM_ARCH_HYV3", text)
        self.assertIn("llama_model_hyv3", text)
        self.assertIn("exit 1", text)
        self.assertIn("-DGGML_CUDA=ON", text)
        self.assertIn("llama-server", text)
        self.assertIn("llama-quantize", text)
        self.assertNotIn("pull --ff-only", text)

    def test_patch_contains_conversion_and_runtime_support(self):
        patch = self.text("patches/llama-cpp-hyv3.patch")
        for marker in (
            "HYV3ForCausalLM",
            "MODEL_ARCH.HYV3",
            "LLM_ARCH_HYV3",
            "llama_model_hyv3",
            "conversion/hyv3.py",
        ):
            self.assertIn(marker, patch)

    def test_docs_state_source_generation_and_deployed_artifact_facts(self):
        readme = self.text("README.md")
        changelog = self.text("CHANGELOG.md")
        combined = readme + changelog
        self.assertIn(
            "https://huggingface.co/GrahLnn/Hy-MT2-30B-A3B-4bit-GGUF",
            readme,
        )
        self.assertIn("tencent/Hy-MT2-30B-A3B", readme)
        self.assertIn("BF16", readme)
        self.assertIn("llama-quantize", readme)
        self.assertIn(
            "f1603f5515a69e4a04b5e989bc7232f71f9120fe7fb980888c0f4b524f38d86a",
            combined,
        )
        self.assertIn("31,985,729,632", combined)
        self.assertRegex(readme, r"(?i)checksum.*pinned|pinned.*checksum")
        self.assertRegex(readme, r"(?i)no direct public Q8|not.*public.*Q8")
        self.assertNotRegex(combined, r"/path/to|<repo>|Q4_K_M")

    def test_gitignore_preserves_worktrees_and_ignores_build_outputs(self):
        text = self.text(".gitignore")
        self.assertNotIn(".worktrees/", text)
        self.assertRegex(text, re.compile(r"(?m)^llama\.cpp/$"))
        self.assertRegex(text, re.compile(r"(?m)^\*\.gguf$"))


if __name__ == "__main__":
    unittest.main()
