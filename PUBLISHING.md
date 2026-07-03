# Publishing

Recommended repository name:

```text
codex-usage-widget
```

Recommended GitHub description:

```text
Unofficial desktop widget for viewing local Codex 5-hour and 7-day usage limits.
```

Recommended topics:

```text
codex, openai, desktop-widget, usage-tracker, rate-limit, python, tkinter, windows, macos, productivity, acrylic, glassmorphism, chinese, zh-cn
```

## Windows Release

Build the Windows archive:

```cmd
build-windows.cmd
```

Upload `dist\CodexUsageWidget-Windows.zip` to the GitHub release.

## First Push

Create an empty GitHub repository first, then run:

```bash
git branch -M main
git remote add origin https://github.com/YOUR_NAME/codex-usage-widget.git
git push -u origin main
```

If this is your first Git commit on this computer, set your identity first:

```bash
git config --global user.name "YOUR_NAME"
git config --global user.email "YOUR_EMAIL"
```
