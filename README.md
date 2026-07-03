# Codex Usage Widget

<p align="center">
  <img src="docs/screenshot.png" alt="Codex Usage Widget live quota screenshot" width="230">
  <img src="docs/hover-screenshot.png" alt="Codex Usage Widget hover glass screenshot" width="230">
  <img src="docs/waiting-screenshot.png" alt="Codex Usage Widget waiting for new Codex record screenshot" width="230">
</p>

<p align="center">
  <strong>A polished desktop widget for checking your local Codex usage limits at a glance.</strong>
  <br>
  <strong>一个用于查看 Codex 5H / 7D 用量的精致桌面小组件。</strong>
</p>

<p align="center">
  <a href="#windows-quick-start">Windows</a>
  |
  <a href="#macos-quick-start">macOS</a>
  |
  <a href="#privacy">Local only</a>
  |
  <a href="#run-tests">Tested</a>
  |
  <a href="docs/PROMOTION.md">Share Kit</a>
</p>

<p align="center">
  <a href="https://github.com/Lijing94-hub/codex-usage-widget/stargazers">
    <img src="https://img.shields.io/github/stars/Lijing94-hub/codex-usage-widget?style=social" alt="GitHub stars">
  </a>
</p>

Codex Usage Widget is built for people who keep Codex open all day and want quota awareness without opening dashboards, digging through logs, or guessing when the next reset happens.

中文用户可以把它当成一个常驻桌面的 Codex 额度看板：不用打开网页，不用翻日志，直接看 5H 和 7D 剩余用量。

It sits quietly on the desktop, shows the two limits that matter most, and makes the important numbers large enough to read at a glance:

- `5H`: the short-window Codex quota
- `7D`: the weekly Codex quota

The interface is intentionally compact and premium-feeling: dark acrylic glass, high-DPI rendering, rounded geometry, Codex branding, color-coded quota bars, hover translucency, and a layout that stays useful even when one window has reset and is waiting for a fresh Codex record.

If this project helps you keep Codex usage visible, a GitHub Star helps more users discover it.

如果这个小组件对你有帮助，欢迎点一个 GitHub Star 支持一下。

## Why It Feels Good

- Beautiful vertical desktop widget that can live near the edge of your screen
- Real local Codex limit snapshots, not mocked counters
- Big remaining-percentage typography for quick scanning
- Green remaining segment and orange used segment for instant visual understanding
- Hover glass mode, so you can inspect content underneath without fully hiding quota data
- Manual refresh, auto refresh, always-on-top mode, and drag-to-position
- Cache fallback when Codex has not written a fresh snapshot yet
- Clear reset/waiting state instead of disappearing or showing misleading values
- System language detection with Simplified Chinese and English UI text
- Windows startup install/uninstall scripts
- macOS launcher included for sharing with teammates
- Built-in tests for parsing, caching, stale windows, and UI rendering

## More Screenshots

| Live quota | Hover glass | Reset-safe state | English UI |
| --- | --- | --- | --- |
| <img src="docs/screenshot.png" alt="Live quota view" width="180"> | <img src="docs/hover-screenshot.png" alt="Hover glass view" width="180"> | <img src="docs/waiting-screenshot.png" alt="Waiting for new Codex record view" width="180"> | <img src="docs/english-screenshot.png" alt="English UI view" width="180"> |

## Privacy

This widget only reads local Codex files under your own `~/.codex` directory.

It does not upload data, does not call a server, and does not read or display your conversation content. The UI only uses local rate-limit snapshots such as remaining percentage, used percentage, reset time, and plan label.

## Windows Quick Start

1. Install Python 3.10+ if you do not already have it.
2. Install Pillow:

   ```powershell
   py -m pip install pillow
   ```

3. Double-click `start.cmd`.

Optional:

- Double-click `install-startup.cmd` to launch it automatically when Windows starts.
- Double-click `uninstall-startup.cmd` to remove startup launch.
- Right-click the widget for refresh, always-on-top, reset position, and quit.

## macOS Quick Start

1. Install Python 3 if needed.
2. Double-click `start-mac.command`.
3. If macOS blocks it, right-click the file and choose Open.

The first launch creates a local `.venv` and installs Pillow automatically.

## Run Tests

Windows:

```powershell
run-tests.cmd
```

Cross-platform:

```bash
python codex_usage_widget.py --test --include-ui
```

## Data Sources

The widget reads local Codex runtime files, including:

- `~/.codex/logs_2.sqlite`
- `~/.codex/sessions/**/*.jsonl`

Successful snapshots are cached locally so the widget can keep showing the last known value if Codex has not emitted a new limit event yet.

Cache locations:

- Windows: `%APPDATA%\CodexUsageWidget\limit_sample.json`
- macOS: `~/Library/Application Support/CodexUsageWidget/limit_sample.json`

## Design Notes

The UI is intentionally narrow and vertical so it can stay visible without stealing the desktop. It uses a restrained dark glass surface, a high-contrast quota hierarchy, and a split quota bar:

- Left side: remaining quota
- Right side: used quota

On hover, the widget lowers window opacity and brightens the acrylic surface, making it possible to inspect whatever is behind it without fully hiding the quota information.

## Disclaimer

This is an unofficial community project and is not affiliated with OpenAI.

Codex and OpenAI are trademarks of their respective owners.
