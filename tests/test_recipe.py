import os
from pathlib import Path
import re
import subprocess
import tempfile
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

    def write_executable(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

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

    def test_start_does_not_duplicate_live_unhealthy_pid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            start = temp / "start.sh"
            start.write_text(self.text("start.sh"), encoding="utf-8")
            model = temp / "model.gguf"
            model.touch()
            launch_marker = temp / "launched"
            server = temp / "llama-server"
            server.write_text(
                '#!/usr/bin/env bash\ntouch "$LAUNCH_MARKER"\n',
                encoding="utf-8",
            )
            server.chmod(0o755)
            curl = temp / "curl"
            curl.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
            curl.chmod(0o755)
            pid_file = temp / ".llama-hymt2.pid"
            pid_file.write_text(str(os.getpid()), encoding="utf-8")
            env = {
                **os.environ,
                "KILL_STUB_MARKER": str(temp / "kill-called"),
                "MODEL": str(model),
                "PATCHED_LLAMA": str(server),
                "LAUNCH_MARKER": str(launch_marker),
                "PATH": f"{temp}:{os.environ['PATH']}",
            }

            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        'kill() { touch "$KILL_STUB_MARKER"; return 0; }; '
                        'export -f kill; exec bash "$1"'
                    ),
                    "_",
                    str(start),
                ],
                env=env,
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("still starting or unhealthy", result.stderr.lower())
            self.assertEqual(pid_file.read_text(encoding="utf-8"), str(os.getpid()))
            self.assertTrue((temp / "kill-called").exists())
            self.assertFalse(launch_marker.exists())

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

    def test_backup_helper_verifies_source_and_destination(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            script = ROOT / "scripts/backup_model.sh"
            model = temp / "Hy-MT2-30B-A3B-Q8_0.gguf"
            model.write_text("test model", encoding="utf-8")
            backup_root = temp / "backup"
            backup_root.mkdir()
            bin_dir = temp / "bin"
            bin_dir.mkdir()
            expected_hash = (
                "f1603f5515a69e4a04b5e989bc7232f71f9120fe7fb980888c0f4b524f38d86a"
            )
            self.write_executable(
                bin_dir / "mountpoint",
                "#!/usr/bin/env bash\nexit 0\n",
            )
            self.write_executable(
                bin_dir / "findmnt",
                '#!/usr/bin/env bash\nprintf "%s\\n" "$BACKUP_ROOT"\n',
            )
            self.write_executable(
                bin_dir / "stat",
                (
                    "#!/usr/bin/env bash\n"
                    'if [[ "$*" == *"%d"* ]]; then\n'
                    '  [[ "${@: -1}" == "/" ]] && echo 1 || echo 2\n'
                    "else\n"
                    '  echo "$EXPECTED_SIZE"\n'
                    "fi\n"
                ),
            )
            self.write_executable(
                bin_dir / "sha256sum",
                (
                    "#!/usr/bin/env bash\n"
                    'printf "%s  %s\\n" "$EXPECTED_HASH" "${@: -1}"\n'
                ),
            )
            self.write_executable(
                bin_dir / "cp",
                (
                    "#!/usr/bin/env bash\n"
                    'touch "$CP_MARKER"\n'
                    'exec /bin/cp "$@"\n'
                ),
            )
            env = {
                **os.environ,
                "BACKUP_ROOT": str(backup_root),
                "CP_MARKER": str(temp / "cp-called"),
                "EXPECTED_HASH": expected_hash,
                "EXPECTED_SIZE": "31985729632",
                "MODEL": str(model),
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
            }

            result = subprocess.run(
                ["bash", str(script), str(backup_root)],
                env=env,
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((temp / "cp-called").exists())
            self.assertTrue((backup_root / model.name).exists())
            self.assertIn("verified backup", result.stdout.lower())

    def test_backup_helper_rejects_same_filesystem_before_copy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            script = ROOT / "scripts/backup_model.sh"
            model = temp / "Hy-MT2-30B-A3B-Q8_0.gguf"
            model.touch()
            backup_root = temp / "backup"
            backup_root.mkdir()
            bin_dir = temp / "bin"
            bin_dir.mkdir()
            self.write_executable(bin_dir / "mountpoint", "#!/bin/sh\nexit 0\n")
            self.write_executable(
                bin_dir / "findmnt",
                '#!/usr/bin/env bash\nprintf "%s\\n" "$BACKUP_ROOT"\n',
            )
            self.write_executable(bin_dir / "stat", "#!/bin/sh\necho 1\n")
            self.write_executable(
                bin_dir / "cp",
                '#!/bin/sh\ntouch "$CP_MARKER"\nexit 0\n',
            )
            env = {
                **os.environ,
                "BACKUP_ROOT": str(backup_root),
                "CP_MARKER": str(temp / "cp-called"),
                "MODEL": str(model),
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
            }

            result = subprocess.run(
                ["bash", str(script), str(backup_root)],
                env=env,
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("different filesystem", result.stderr.lower())
            self.assertFalse((temp / "cp-called").exists())

    def test_backup_helper_rejects_source_checksum_before_copy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            script = ROOT / "scripts/backup_model.sh"
            model = temp / "Hy-MT2-30B-A3B-Q8_0.gguf"
            model.touch()
            backup_root = temp / "backup"
            backup_root.mkdir()
            bin_dir = temp / "bin"
            bin_dir.mkdir()
            self.write_executable(bin_dir / "mountpoint", "#!/bin/sh\nexit 0\n")
            self.write_executable(
                bin_dir / "findmnt",
                '#!/usr/bin/env bash\nprintf "%s\\n" "$BACKUP_ROOT"\n',
            )
            self.write_executable(
                bin_dir / "stat",
                (
                    "#!/usr/bin/env bash\n"
                    'if [[ "$*" == *"%d"* ]]; then\n'
                    '  [[ "${@: -1}" == "/" ]] && echo 1 || echo 2\n'
                    "else\n"
                    "  echo 31985729632\n"
                    "fi\n"
                ),
            )
            self.write_executable(
                bin_dir / "sha256sum",
                '#!/bin/sh\necho "bad-hash  $1"\n',
            )
            self.write_executable(
                bin_dir / "cp",
                '#!/bin/sh\ntouch "$CP_MARKER"\nexit 0\n',
            )
            env = {
                **os.environ,
                "BACKUP_ROOT": str(backup_root),
                "CP_MARKER": str(temp / "cp-called"),
                "MODEL": str(model),
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
            }

            result = subprocess.run(
                ["bash", str(script), str(backup_root)],
                env=env,
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("source sha256", result.stderr.lower())
            self.assertFalse((temp / "cp-called").exists())

    def test_backup_helper_rejects_symlink_destination(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            script = ROOT / "scripts/backup_model.sh"
            real_root = temp / "real"
            real_root.mkdir()
            backup_root = temp / "backup"
            backup_root.symlink_to(real_root, target_is_directory=True)
            result = subprocess.run(
                ["bash", str(script), str(backup_root)],
                env={**os.environ, "MODEL": str(temp / "model.gguf")},
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink", result.stderr.lower())

    def test_backup_helper_publishes_without_overwriting(self):
        text = self.text("scripts/backup_model.sh")
        self.assertIn('ln -- "$TEMP_FILE" "$DESTINATION"', text)
        self.assertNotIn("mv --no-clobber", text)

    def test_docs_state_local_only_unknown_provenance_and_artifact_facts(self):
        readme = self.text("README.md")
        changelog = self.text("CHANGELOG.md")
        combined = readme + changelog
        self.assertIn(
            "https://huggingface.co/GrahLnn/Hy-MT2-30B-A3B-4bit-GGUF",
            readme,
        )
        self.assertIn("tencent/Hy-MT2-30B-A3B", readme)
        self.assertIn("4ae7787", readme)
        self.assertIn(
            "f1603f5515a69e4a04b5e989bc7232f71f9120fe7fb980888c0f4b524f38d86a",
            combined,
        )
        self.assertIn("31,985,729,632", combined)
        self.assertRegex(readme, r"(?i)local-only")
        self.assertRegex(readme, r"(?i)unknown provenance")
        self.assertRegex(readme, r"(?i)back up.*separately.*before.*wipe")
        self.assertNotIn("Hy-MT2-30B-A3B-BF16.gguf", combined)
        self.assertNotRegex(combined, r"(?i)BF16-to-Q8|reproduce.*Q8|regenerate.*Q8")
        self.assertNotRegex(combined, r"(?i)direct public Q8.*artifact")
        self.assertNotRegex(combined, r"/path/to|<repo>|Q4_K_M")

    def test_service_installer_preserves_original_backup_across_repeated_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            unit_dir = temp / "systemd"
            unit_dir.mkdir()
            unit_path = unit_dir / "llama-hymt2.service"
            unit_path.write_text("original unit\n", encoding="utf-8")
            bin_dir = temp / "bin"
            bin_dir.mkdir()
            self.write_executable(
                bin_dir / "systemctl",
                '#!/bin/sh\nprintf "%s\\n" "$*" >> "$SYSTEMCTL_LOG"\n',
            )
            env = {
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "SYSTEMCTL_LOG": str(temp / "systemctl.log"),
                "UNIT_DIR": str(unit_dir),
            }
            script = ROOT / "scripts/install_service.sh"

            first = subprocess.run(
                ["bash", str(script)],
                env=env,
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
            second = subprocess.run(
                ["bash", str(script)],
                env=env,
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(
                (unit_dir / "llama-hymt2.service.backup").read_text(
                    encoding="utf-8"
                ),
                "original unit\n",
            )
            self.assertEqual(
                unit_path.read_text(encoding="utf-8"),
                self.text("systemd/llama-hymt2.service"),
            )

    def test_docs_use_safe_service_installer_and_restore_backup(self):
        readme = self.text("README.md")
        self.assertIn("./scripts/install_service.sh", readme)
        self.assertIn(
            'if [[ -f "$BACKUP_PATH" ]]; then\n'
            '  cp "$BACKUP_PATH" "$UNIT_PATH"\n'
            "else\n"
            '  echo "No saved unit backup found at $BACKUP_PATH" >&2\n'
            "  exit 1\n"
            "fi",
            readme,
        )
        self.assertIn("systemctl --user daemon-reload", readme)
        self.assertIn("systemctl --user enable --now llama-hymt2.service", readme)

    def test_docs_use_backup_helper_and_verify_model_hash_and_size(self):
        readme = self.text("README.md")
        self.assertIn("./scripts/backup_model.sh /mnt/model-backup", readme)
        self.assertIn('EXPECTED_SHA256="f1603f5515a69e4a04b5e989bc7232f71f9120fe7fb980888c0f4b524f38d86a"', readme)
        self.assertIn('EXPECTED_SIZE="31985729632"', readme)
        self.assertIn('[[ "$(sha256sum "$MODEL" | awk \'{print $1}\')" == "$EXPECTED_SHA256" ]]', readme)
        self.assertIn('[[ "$(stat -c %s -- "$MODEL")" == "$EXPECTED_SIZE" ]]', readme)

    def test_gitignore_preserves_worktrees_and_ignores_build_outputs(self):
        text = self.text(".gitignore")
        self.assertIn(".worktrees/", text)
        self.assertRegex(text, re.compile(r"(?m)^llama\.cpp/$"))
        self.assertRegex(text, re.compile(r"(?m)^\*\.gguf$"))


if __name__ == "__main__":
    unittest.main()
