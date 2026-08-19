# Changelog

All notable changes to Codex Vision are documented here.

## [1.0.1] - 2026-08-19

### Fixed

- Built release packages with the Python runtime selected by GitHub Actions so Tcl/Tk data is included reliably.
- Added a packaged-EXE self-test gate before GitHub can publish a Windows release.
- Added a SHA-256 checksum beside every release archive.

## [1.0.0] - 2026-08-19

### Added

- Windows taskbar-free desktop-widget mode.
- Direct weekly-quota sync through the locally installed Codex app-server.
- Local log and session fallback with persistent last-known-good snapshots.
- Confirmed billing dates and Codex reset-credit display.
- Simplified Chinese and English system-language UI.
- Reproducible high-resolution documentation screenshots.

### Changed

- Renamed the product to Codex Vision and standardized all public assets.
- Reduced background app-server retries after a failed sync.
- Made JSON cache writes collision-safe and crash-resistant.
- Improved scaled hit testing for refresh, close and plan controls.
- Declared Windows 10/11 as the only supported platform.

### Removed

- macOS launcher, documentation and promotional claims.
- Obsolete icon generations, old concept renders and repository bootstrap scripts.

## [0.1.0] - 2026-07-03

- Initial public prototype.
