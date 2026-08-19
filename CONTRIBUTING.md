# Contributing

Thank you for helping improve Codex Vision.

## Scope

Codex Vision supports Windows 10 and Windows 11 only. Please do not submit macOS or Linux launchers, packaging changes or platform claims.

## Before Opening An Issue

- Install the latest release.
- Confirm that Codex itself can report account usage.
- Remove account names, tokens, cookies and conversation content from screenshots and logs.
- Search existing issues for the same behavior.

## Development Checklist

1. Keep changes focused and preserve the local-first privacy model.
2. Add or update tests for parser, cache, refresh or interaction changes.
3. Run `python -m py_compile codex_usage_widget.py`.
4. Run `python codex_usage_widget.py --test --include-ui`.
5. For UI changes, regenerate docs with `python tools\generate_docs_assets.py` and inspect every output image.
6. For packaging changes, run `build-windows.cmd` and test the packaged EXE.

Do not commit `dist/`, `build/`, virtual environments, local configuration, logs or private Codex files.

## Pull Requests

Describe the user-visible problem, the chosen fix, test evidence and remaining risk. Keep unrelated refactors in separate pull requests.
