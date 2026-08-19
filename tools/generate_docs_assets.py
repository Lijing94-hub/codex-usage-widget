from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import codex_usage_widget as widget  # noqa: E402

DOCS = ROOT / "docs"
ICON = ROOT / "assets" / "spyglass-codex-v8-clean-frame.png"
FONT_REGULAR = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_BOLD = Path(r"C:\Windows\Fonts\msyhbd.ttc")
FONT_UI = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_UI_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")


def font(size: int, *, bold: bool = False, latin: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_UI_BOLD if latin and bold else FONT_UI if latin else FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(str(path), size)


def live_sample() -> dict:
    now = time.time()
    raw = {
        "primary": {
            "used_percent": 37,
            "window_minutes": widget.WEEKLY_MINUTES,
            "resets_at": now + (6 * 24 + 10) * 3600,
        },
        "secondary": None,
    }
    sample = widget.empty_sample()
    sample.update(
        {
            "ok": True,
            "source_state": "live",
            "source_event_at": now,
            "snapshot_at": now,
            "plan_type": "plus",
            "plan_expires_at": dt.datetime(2030, 9, 24, 17, 15).astimezone().timestamp(),
            "plan_expires_source": "billing_confirmed",
            "resets_remaining": 2,
            "resets_source": "credits",
            "windows": widget.normalize_rate_limits(raw, now=now),
        }
    )
    return sample


def renderer() -> widget.CardRenderer:
    result = widget.CardRenderer()
    result.WIDTH = result.DESIGN_WIDTH * result.SCALE
    result.HEIGHT = result.DESIGN_HEIGHT * result.SCALE
    result.CORNER_RADIUS = 28 * result.SCALE
    return result


def save_widget_screenshots() -> None:
    previous = widget.CURRENT_LANGUAGE
    try:
        sample = live_sample()
        widget.CURRENT_LANGUAGE = "zh"
        current = renderer()
        current.render_rgba(sample).save(DOCS / "screenshot.png")
        current.render_rgba(sample, hover=True).save(DOCS / "hover-screenshot.png")

        waiting = widget.empty_sample()
        waiting["source_state"] = "unavailable"
        waiting["plan_expires_source"] = "billing_required"
        waiting["note"] = widget.tr("note_no_snapshot")
        current.render_rgba(waiting).save(DOCS / "waiting-screenshot.png")

        widget.CURRENT_LANGUAGE = "en"
        renderer().render_rgba(sample).save(DOCS / "english-screenshot.png")
    finally:
        widget.CURRENT_LANGUAGE = previous


def paste_with_shadow(canvas: Image.Image, image: Image.Image, xy: tuple[int, int]) -> None:
    x, y = xy
    alpha = image.getchannel("A")
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    mask = Image.new("L", canvas.size, 0)
    mask.paste(alpha, (x, y + 12))
    mask = mask.filter(ImageFilter.GaussianBlur(26))
    shadow.putalpha(mask.point(lambda value: value * 120 // 255))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(image, xy)


def save_social_preview() -> None:
    canvas = Image.new("RGBA", (1200, 630), "#0B1017")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((815, 0, 1200, 630), fill="#17222C")
    draw.line((64, 58, 1136, 58), fill="#34404A", width=1)
    draw.line((64, 570, 1136, 570), fill="#34404A", width=1)

    icon = Image.open(ICON).convert("RGBA").resize((82, 82), Image.Resampling.LANCZOS)
    canvas.alpha_composite(icon, (66, 92))
    draw.text((172, 94), "Codex Vision", font=font(58, bold=True, latin=True), fill="#F4F7F9")
    draw.text((174, 157), "清晰掌握，从容创作", font=font(25), fill="#97A5B1")

    draw.text((66, 248), "周额度，一眼看清", font=font(52, bold=True), fill="#F4F7F9")
    draw.rounded_rectangle((68, 325, 181, 334), radius=4, fill="#65E39A")
    draw.rounded_rectangle((190, 325, 248, 334), radius=4, fill="#F47C59")
    draw.text((66, 370), "7D 周额度  ·  套餐到期  ·  重置次数", font=font(27, bold=True), fill="#CBD3DA")
    draw.text((66, 422), "本地读取 · 自动同步 · Windows 专属", font=font(23), fill="#81909C")

    screenshot = Image.open(DOCS / "screenshot.png").convert("RGBA")
    width = 292
    screenshot = screenshot.resize((width, round(width * screenshot.height / screenshot.width)), Image.Resampling.LANCZOS)
    paste_with_shadow(canvas, screenshot, (855, 61))

    draw.text((66, 590), "github.com/Lijing94-hub/codex-usage-widget", font=font(19, bold=True, latin=True), fill="#AAB6C0")
    draw.text((1012, 590), "OPEN SOURCE", font=font(17, bold=True, latin=True), fill="#65E39A")
    canvas.convert("RGB").save(DOCS / "social-preview.png", quality=96)


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    save_widget_screenshots()
    save_social_preview()


if __name__ == "__main__":
    main()
