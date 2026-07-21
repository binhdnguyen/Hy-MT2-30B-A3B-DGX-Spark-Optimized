# Changelog

## [1.1.2] - 2026-07-21

### Fixed

- Added a fail-closed model backup helper that requires a separate mounted filesystem and verifies exact source and destination size and SHA256.
- Added automatic exact hash and size checks to documented model installation and restoration.
- Added a service installer that creates the original `.backup` once and preserves it across repeated installations.

## [1.1.1] - 2026-07-21

### Fixed

- Prevented `start.sh` from launching a duplicate server when the recorded PID is alive but its health endpoint is not ready.
- Corrected Q8_0 provenance after inspecting related model repository commit `4ae7787`: the deployed artifact is local-only, has unknown provenance, and has no established download or generation path.
- Added model-backup guidance and safe systemd unit backup and restoration commands.

## [1.1.0] - 2026-07-21

### Changed

- Synced the recipe to the verified Q8_0 deployment on port 8002.
- Added portable `$HOME`/`%h` defaults and the complete live server flag set, including `--temp 0.7`.
- Pinned llama.cpp to `c57607016a1ebdd08d269e3378eee5546fc3bf3a` and included the verified HYV3 patch and preparation script.
- Updated the systemd unit with NVIDIA readiness, unlimited start retries, `Restart=always`, and verified timeouts.
- Replaced stale Q4 and placeholder instructions with Q8_0 deployment, install, health, and restore steps.

### Verified artifact

- File: `Hy-MT2-30B-A3B-Q8_0.gguf`
- Size: 31,985,729,632 bytes
- SHA256: `f1603f5515a69e4a04b5e989bc7232f71f9120fe7fb980888c0f4b524f38d86a`
- The exact Q8_0 file is local-only and of unknown provenance.

## [1.0.0] - 2026-07-09

### Added

- Initial helper scripts and systemd recipe.
