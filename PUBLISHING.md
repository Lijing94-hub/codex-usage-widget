# Release Guide

Codex Vision is a Windows-only product. Release notes, screenshots, repository metadata and binaries must not claim macOS support.

## Repository Metadata

Description:

```text
Windows desktop widget for Codex 7-day usage, plan expiration and reset credits.
```

Topics:

```text
codex, openai, windows, desktop-widget, usage-tracker, rate-limit, python, tkinter, productivity, acrylic, local-first, chinese, zh-cn
```

## Release Checklist

1. Update `APP_RELEASE_VERSION` and `CHANGELOG.md`.
2. Run `python tools\generate_docs_assets.py` and visually inspect every image under `docs/`.
3. Run `python -m py_compile codex_usage_widget.py`.
4. Run `python codex_usage_widget.py --test --include-ui`.
5. Run `build-windows.cmd` on Windows.
6. Run `tools/test_windows_install.ps1` against the package and verify all three shortcuts.
7. Start the packaged EXE and verify refresh, drag, hover, plan-date dialog, taskbar hiding, taskbar pin request and close.
8. Commit and push the release changes.
9. Create and push an annotated `vX.Y.Z` tag. The release workflow builds and uploads `CodexVision-Windows.zip`.

## Release Notes

Every release must state:

- supported Windows versions;
- visible product changes;
- data-source or privacy changes;
- known limitations;
- whether the build is code-signed.

Do not include local account data, private screenshots or files from `%APPDATA%\CodexUsageWidget`.
