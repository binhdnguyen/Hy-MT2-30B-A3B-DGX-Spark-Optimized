# Changelog

## [1.1.0] - 2026-07-21

### Changed

- Synced the recipe to the verified Q8_0 deployment on port 8002.
- Added portable `$HOME`/`%h` defaults and the complete live server flag set, including `--temp 0.7`.
- Pinned llama.cpp to `c57607016a1ebdd08d269e3378eee5546fc3bf3a` and included the verified HYV3 patch and preparation script.
- Updated the systemd unit with NVIDIA readiness, unlimited start retries, `Restart=always`, and verified timeouts.
- Replaced stale Q4 and placeholder instructions with BF16-to-Q8_0 reproduction, install, health, and restore steps.

### Verified artifact

- File: `Hy-MT2-30B-A3B-Q8_0.gguf`
- Size: 31,985,729,632 bytes
- SHA256: `f1603f5515a69e4a04b5e989bc7232f71f9120fe7fb980888c0f4b524f38d86a`
- The exact Q8_0 file is not currently a direct public artifact in the cited source repository.

## [1.0.0] - 2026-07-09

### Added

- Initial helper scripts and systemd recipe.
