# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import base64
import contextlib
import ctypes
import datetime as dt
import json
import locale
import math
import os
import pathlib
import queue
import sqlite3
import sys
import tempfile
import threading
import time
import traceback
import unittest
from typing import Any, Callable

try:
    import tkinter as tk
    from tkinter import messagebox
except Exception:  # pragma: no cover - reported by run_app()
    tk = None
    messagebox = None

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageTk
except Exception:  # pragma: no cover - tests cover non-UI logic without PIL
    Image = None
    ImageChops = None
    ImageDraw = None
    ImageFilter = None
    ImageFont = None
    ImageTk = None


APP_NAME = "Codex Usage Widget"
APP_VERSION = 3


def runtime_app_dir() -> pathlib.Path:
    if getattr(sys, "frozen", False):
        return pathlib.Path(sys.executable).resolve().parent
    return pathlib.Path(__file__).resolve().parent


def runtime_resource_dir() -> pathlib.Path:
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return pathlib.Path(bundled)
    return pathlib.Path(__file__).resolve().parent


APP_DIR = runtime_app_dir()
RESOURCE_DIR = runtime_resource_dir()
ASSET_DIR = RESOURCE_DIR / "assets"
ICON_PATH = ASSET_DIR / "codex-usage.ico"
CODEX_MARK_PATH = ASSET_DIR / "codex-color.png"
WIDGET_MARK_PATH = ASSET_DIR / "spyglass-codex-v8-clean-frame.png"
SPYGLASS_BASE_PATH = WIDGET_MARK_PATH
GLASS_PANEL_PATH = ASSET_DIR / "image2-glass-panel.png"


def default_data_dir() -> pathlib.Path:
    if sys.platform == "darwin":
        return pathlib.Path.home() / "Library" / "Application Support" / "CodexUsageWidget"
    if os.environ.get("APPDATA"):
        return pathlib.Path(os.environ["APPDATA"]) / "CodexUsageWidget"
    return APP_DIR / "CodexUsageWidget"


DATA_DIR = default_data_dir()
CONFIG_PATH = DATA_DIR / "config.json"
CACHE_PATH = DATA_DIR / "limit_sample.json"
LOG_PATH = DATA_DIR / "widget.log"

FIVE_HOUR_MINUTES = 5 * 60
WEEKLY_MINUTES = 7 * 24 * 60
DEFAULT_REFRESH_SECONDS = 6
SESSION_TAIL_BYTES = 768 * 1024
MAX_SESSION_FILES = 120

DEFAULT_CONFIG: dict[str, Any] = {
    "refresh_seconds": DEFAULT_REFRESH_SECONDS,
    "always_on_top": True,
    "window_x": None,
    "window_y": None,
    "codex_home": None,
    "language": "system",
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "app_name": "Codex Usage Widget",
        "subtitle": "quota at a glance",
        "status_refreshing": "Refreshing",
        "status_unchanged": "No update",
        "status_cache": "Cached",
        "status_waiting": "Waiting",
        "status_stale": "Needs refresh",
        "status_live": "Live",
        "status_updated": "Synced",
        "window_5h": "5H window",
        "window_7d": "7D window",
        "remaining": "Remaining",
        "plan_expires": "Plan ends",
        "resets_left": "Resets left",
        "weekly_cycle": "Future resets only",
        "codex_credits": "From Codex credits",
        "times_left": "{value} left",
        "used": "Used",
        "waiting": "Waiting",
        "waiting_snapshot": "Waiting snapshot",
        "not_applicable": "N/A",
        "model_no_5h": "No 5H window for current model",
        "reset_done": "Reset",
        "stale_snapshot": "Waiting for new Codex record",
        "reset": " to reset",
        "unknown": "Unknown",
        "unknown_time": "Unknown time",
        "reset_reached": "Reset reached",
        "minute_after": "m",
        "hour_after": "h",
        "hour_min_after": "{hours}h {mins}m",
        "day_after": "{days}d",
        "day_hour_after": "{days}d {hours}h",
        "just_now": "Just now",
        "minute_ago": "{value} min ago",
        "hour_ago": "{value} h ago",
        "day_ago": "{value} d ago",
        "footer_refreshing": "Refreshing",
        "footer_unchanged": "No update · {age}",
        "footer_updated": "Updated {age}",
        "footer_cache": "Cached · {age}",
        "footer_waiting": "Waiting for Codex limit data",
        "footer_usage_changed": "Used {delta}% · just now",
        "menu_refresh": "Refresh now",
        "menu_topmost": "Always on top / off",
        "menu_reset": "Reset to top right",
        "menu_quit": "Quit",
        "pending_read": "Reading Codex limits",
        "pending_refresh": "Finding latest limit snapshot",
        "manual_unchanged": "Refresh finished, but no new limit snapshot was found",
        "tk_missing": "Cannot start window UI: tkinter is unavailable.",
        "pillow_missing": "Cannot start window UI: Pillow is unavailable.",
        "ui_crashed": "Widget failed to start. Log file:\n{path}",
        "arg_test": "Run self tests",
        "arg_include_ui": "Include UI smoke test",
        "arg_snapshot": "Print current limit snapshot",
        "arg_make_icon": "Regenerate high-resolution icon",
        "note_no_snapshot": "No new limit snapshot was found",
        "note_new_record": "It will refresh after Codex writes a new record",
        "note_unrecognized": "Limit records were found, but 5-hour or 7-day windows were not recognized",
        "note_format_changed": "Codex local record format may have changed",
        "note_stale": "A limit window has reached its reset point. It will update after your next Codex activity",
        "note_local": "From local Codex limit records",
        "note_cache": "Showing cached data",
        "note_cache_fallback": "Live read failed, showing last successful data: {error}",
        "note_cache_no_new": "No fresh snapshot yet, showing last successful data",
        "note_failed": "Read failed temporarily",
    },
    "zh": {
        "app_name": "Codex 用量小组件",
        "subtitle": "额度一眼看清",
        "status_refreshing": "刷新中",
        "status_unchanged": "无新快照",
        "status_cache": "缓存",
        "status_waiting": "等待数据",
        "status_stale": "待刷新",
        "status_live": "实时",
        "status_updated": "已同步",
        "window_5h": "5 小时窗口",
        "window_7d": "1 周窗口",
        "remaining": "剩余",
        "plan_expires": "套餐到期",
        "resets_left": "剩余重置",
        "weekly_cycle": "仅含后续重置",
        "codex_credits": "来自 Codex 额度",
        "times_left": "{value} 次",
        "used": "已用",
        "waiting": "等待",
        "waiting_snapshot": "等待快照",
        "not_applicable": "不适用",
        "model_no_5h": "当前模型无 5H 窗口",
        "reset_done": "已重置",
        "stale_snapshot": "等待 Codex 新记录",
        "reset": "重置",
        "unknown": "未知",
        "unknown_time": "未知时间",
        "reset_reached": "已到重置时间",
        "minute_after": " 分钟后",
        "hour_after": " 小时后",
        "hour_min_after": "{hours} 小时 {mins} 分后",
        "day_after": "{days} 天后",
        "day_hour_after": "{days} 天 {hours} 小时后",
        "just_now": "刚刚",
        "minute_ago": "{value} 分钟前",
        "hour_ago": "{value} 小时前",
        "day_ago": "{value} 天前",
        "footer_refreshing": "正在刷新",
        "footer_unchanged": "无新快照 · {age}",
        "footer_updated": "更新 {age}",
        "footer_cache": "缓存 · {age}",
        "footer_waiting": "等待 Codex 额度数据",
        "footer_usage_changed": "已用 {delta}% · 刚刚",
        "menu_refresh": "立即刷新",
        "menu_topmost": "置顶 / 取消置顶",
        "menu_reset": "回到右上角",
        "menu_quit": "退出",
        "pending_read": "正在读取 Codex 额度",
        "pending_refresh": "正在查找最新额度快照",
        "manual_unchanged": "刷新完成，但没有新的额度快照",
        "tk_missing": "无法启动窗口组件：tkinter 不可用。",
        "pillow_missing": "无法启动窗口组件：Pillow 不可用。",
        "ui_crashed": "小组件启动失败，日志在：\n{path}",
        "arg_test": "运行自测",
        "arg_include_ui": "自测时包含窗口烟雾测试",
        "arg_snapshot": "打印当前读取到的额度快照",
        "arg_make_icon": "重新生成高分辨率图标",
        "note_no_snapshot": "没有找到新的额度快照",
        "note_new_record": "Codex 写入新记录后会自动刷新",
        "note_unrecognized": "读到了额度记录，但没有识别出 5 小时或 1 周窗口",
        "note_format_changed": "Codex 记录格式可能更新了",
        "note_stale": "额度窗口已经到过重置点，继续一次 Codex 后会更新",
        "note_local": "来自 Codex 本地额度记录",
        "note_cache": "显示缓存数据",
        "note_cache_fallback": "当前读取失败，显示上次成功数据：{error}",
        "note_cache_no_new": "暂时没读到新快照，显示上次成功数据",
        "note_failed": "暂时读取失败",
    },
}


def system_language() -> str:
    configured = os.environ.get("CODEX_USAGE_WIDGET_LANG", "").strip().lower()
    if configured:
        return "zh" if configured.startswith("zh") else "en"
    if sys.platform == "win32":
        with contextlib.suppress(Exception):
            buffer = ctypes.create_unicode_buffer(85)
            if ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, len(buffer)):
                return "zh" if buffer.value.lower().startswith("zh") else "en"
    candidates = [
        locale.getlocale()[0],
        os.environ.get("LANG"),
        os.environ.get("LANGUAGE"),
    ]
    for value in candidates:
        if value and str(value).lower().startswith("zh"):
            return "zh"
    return "en"


CURRENT_LANGUAGE = system_language()


def tr(key: str, **kwargs: Any) -> str:
    text = TRANSLATIONS.get(CURRENT_LANGUAGE, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))
    return text.format(**kwargs) if kwargs else text


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def log_line(message: str) -> None:
    try:
        ensure_data_dir()
        stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"[{stamp}] {message}\n")
    except Exception:
        pass


def load_json(path: pathlib.Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_line(f"Failed to load {path}: {exc}")
    return default


def atomic_write_json(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def clean_int(value: Any, minimum: int | None = None, maximum: int | None = None) -> int | None:
    if value in ("", None):
        return None
    try:
        parsed = int(float(str(value).replace(",", "").strip()))
    except Exception:
        return None
    if minimum is not None and parsed < minimum:
        return None
    if maximum is not None and parsed > maximum:
        return maximum
    return parsed


def clean_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        parsed = float(str(value).strip())
    except Exception:
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def load_config() -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    user_config = load_json(CONFIG_PATH, {})
    if isinstance(user_config, dict):
        config.update(user_config)
    refresh_seconds = clean_int(config.get("refresh_seconds"), 3, 3600) or DEFAULT_REFRESH_SECONDS
    config["refresh_seconds"] = DEFAULT_REFRESH_SECONDS if refresh_seconds in (20, 25) else refresh_seconds
    config["window_x"] = clean_int(config.get("window_x"))
    config["window_y"] = clean_int(config.get("window_y"))
    config["always_on_top"] = bool(config.get("always_on_top", True))
    if config.get("codex_home"):
        config["codex_home"] = str(config["codex_home"])
    return config


def save_config(config: dict[str, Any]) -> None:
    to_write = dict(DEFAULT_CONFIG)
    to_write.update(config)
    atomic_write_json(CONFIG_PATH, to_write)


def codex_home_from_config(config: dict[str, Any]) -> pathlib.Path:
    configured = config.get("codex_home") or os.environ.get("CODEX_HOME")
    if configured:
        return pathlib.Path(str(configured)).expanduser()
    return pathlib.Path(os.environ.get("USERPROFILE") or str(pathlib.Path.home())) / ".codex"


def read_local_plan_metadata(codex_home: pathlib.Path) -> dict[str, Any]:
    metadata = {"plan_type": None, "plan_expires_at": None, "plan_checked_at": None}
    auth = load_json(codex_home / "auth.json", {})
    if not isinstance(auth, dict):
        return metadata
    tokens = auth.get("tokens")
    token = tokens.get("id_token") if isinstance(tokens, dict) else None
    if not isinstance(token, str):
        return metadata
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return metadata
        encoded = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded).decode("utf-8"))
        account = payload.get("https://api.openai.com/auth")
        if not isinstance(account, dict):
            return metadata
        metadata["plan_type"] = account.get("chatgpt_plan_type")
        metadata["plan_expires_at"] = parse_event_timestamp(account.get("chatgpt_subscription_active_until"))
        metadata["plan_checked_at"] = parse_event_timestamp(account.get("chatgpt_subscription_last_checked"))
    except Exception as exc:
        log_line(f"Failed to read local plan metadata: {exc}")
    return metadata


def resets_before_expiry(
    next_reset: Any,
    plan_expires_at: Any,
    now: Any = None,
) -> int | None:
    reset_ts = clean_float(next_reset)
    expiry_ts = clean_float(plan_expires_at)
    if reset_ts is None or expiry_ts is None:
        return None
    if reset_ts > 10_000_000_000:
        reset_ts /= 1000
    if expiry_ts > 10_000_000_000:
        expiry_ts /= 1000
    current_ts = now_ts() if now is None else clean_float(now)
    if current_ts is None:
        current_ts = now_ts()
    if current_ts > 10_000_000_000:
        current_ts /= 1000
    if reset_ts <= 0 or expiry_ts <= current_ts:
        return 0

    cycle_seconds = WEEKLY_MINUTES * 60
    if reset_ts <= current_ts:
        elapsed_cycles = math.floor((current_ts - reset_ts) / cycle_seconds) + 1
        reset_ts += elapsed_cycles * cycle_seconds

    return math.ceil((expiry_ts - reset_ts) / cycle_seconds) if reset_ts < expiry_ts else 0


def resets_from_credits(raw: dict[str, Any]) -> int | None:
    credits = raw.get("credits")
    if not isinstance(credits, dict) or credits.get("unlimited") is True:
        return None
    balance = clean_int(credits.get("balance"), minimum=0)
    if balance is not None:
        return balance
    return 0 if credits.get("has_credits") is False else None


def now_ts() -> float:
    return time.time()


def parse_event_timestamp(value: Any) -> float | None:
    if value in ("", None):
        return None
    numeric = clean_float(value)
    if numeric is not None and numeric > 0:
        return numeric / 1000 if numeric > 10_000_000_000 else numeric
    try:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = dt.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.timestamp()
    except Exception:
        return None


def format_local_time(timestamp: Any, include_date: bool = False) -> str:
    ts = clean_float(timestamp)
    if ts is None or ts <= 0:
        return tr("unknown")
    if ts > 10_000_000_000:
        ts /= 1000
    try:
        value = dt.datetime.fromtimestamp(ts).astimezone()
    except Exception:
        return tr("unknown")
    if include_date:
        return value.strftime("%m月%d日 %H:%M") if CURRENT_LANGUAGE == "zh" else value.strftime("%b %d %H:%M")
    return value.strftime("%H:%M")


def format_relative(timestamp: Any, now: float | None = None) -> str:
    ts = clean_float(timestamp)
    if ts is None or ts <= 0:
        return tr("unknown")
    if ts > 10_000_000_000:
        ts /= 1000
    now = now_ts() if now is None else now
    delta = ts - now
    if delta <= 0:
        return tr("reset_reached")
    minutes = int(round(delta / 60))
    if minutes < 60:
        return f"{max(1, minutes)}{tr('minute_after')}"
    hours, mins = divmod(minutes, 60)
    if hours < 36:
        return tr("hour_min_after", hours=hours, mins=mins) if mins else f"{hours}{tr('hour_after')}"
    days, hours = divmod(hours, 24)
    return tr("day_hour_after", days=days, hours=hours) if hours else tr("day_after", days=days)


def format_age(timestamp: Any, now: float | None = None) -> str:
    ts = clean_float(timestamp)
    if ts is None or ts <= 0:
        return tr("unknown_time")
    if ts > 10_000_000_000:
        ts /= 1000
    now = now_ts() if now is None else now
    age = max(0, int(now - ts))
    if age < 75:
        return tr("just_now")
    if age < 3600:
        return tr("minute_ago", value=age // 60)
    if age < 36 * 3600:
        return tr("hour_ago", value=age // 3600)
    return tr("day_ago", value=age // 86400)


def empty_window() -> dict[str, Any]:
    return {
        "available": False,
        "label": "",
        "used_percent": None,
        "remaining_percent": None,
        "reset_at": None,
        "window_minutes": None,
        "stale": False,
        "not_offered": False,
    }


def empty_sample(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = {} if config is None else config
    return {
        "app": tr("app_name"),
        "version": APP_VERSION,
        "ok": False,
        "source_state": "unavailable",
        "snapshot_at": now_ts(),
        "source_event_at": None,
        "source_path": None,
        "codex_home": str(codex_home_from_config(config)),
        "plan_type": None,
        "plan_expires_at": None,
        "plan_checked_at": None,
        "resets_remaining": None,
        "resets_source": None,
        "limit_id": None,
        "rate_limit_reached_type": None,
        "windows": {
            "five_hour": empty_window() | {"label": tr("window_5h")},
            "weekly": empty_window() | {"label": tr("window_7d")},
        },
        "errors": [],
        "note": "",
    }


def iter_rate_limit_payloads(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def walk(node: Any, depth: int = 0) -> None:
        if depth > 8:
            return
        if isinstance(node, dict):
            direct = node.get("rate_limits")
            if isinstance(direct, dict):
                found.append(direct)
            singular = node.get("rate_limit")
            if isinstance(singular, dict):
                found.append(singular)
            if any(key in node for key in ("primary", "secondary", "primary_window", "secondary_window")):
                found.append(node)
            for child in node.values():
                if isinstance(child, (dict, list)):
                    walk(child, depth + 1)
        elif isinstance(node, list):
            for child in node:
                if isinstance(child, (dict, list)):
                    walk(child, depth + 1)

    walk(value)
    unique: list[dict[str, Any]] = []
    seen: set[int] = set()
    for item in found:
        ident = id(item)
        if ident not in seen:
            seen.add(ident)
            unique.append(item)
    return unique


def window_minutes_from(data: dict[str, Any]) -> int | None:
    minutes = clean_float(
        data.get("window_minutes")
        or data.get("limit_window_minutes")
        or data.get("rolling_window_minutes")
    )
    if minutes is not None and minutes > 0:
        return int(round(minutes))
    seconds = clean_float(
        data.get("limit_window_seconds")
        or data.get("window_seconds")
        or data.get("rolling_window_seconds")
    )
    if seconds is not None and seconds > 0:
        return int(round(seconds / 60))
    return None


def reset_timestamp_from(data: dict[str, Any]) -> float | None:
    return parse_event_timestamp(data.get("resets_at") or data.get("reset_at") or data.get("resetAt"))


def normalize_window(data: dict[str, Any], label: str, now: float | None = None) -> dict[str, Any] | None:
    minutes = window_minutes_from(data)
    used = clean_float(data.get("used_percent") or data.get("usage_percent") or data.get("usedPercentage"))
    reset_at = reset_timestamp_from(data)
    if minutes is None and used is None and reset_at is None:
        return None
    used = clamp(used if used is not None else 0.0, 0.0, 100.0)
    remaining = clamp(100.0 - used, 0.0, 100.0)
    current = now_ts() if now is None else now
    return {
        "available": True,
        "label": label,
        "used_percent": round(used, 1),
        "remaining_percent": round(remaining, 1),
        "reset_at": reset_at,
        "window_minutes": minutes,
        "stale": bool(reset_at is not None and reset_at <= current),
    }


def candidate_windows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for key in ("primary", "secondary", "primary_window", "secondary_window"):
        value = raw.get(key)
        if isinstance(value, dict):
            candidates.append(value)
    additional = raw.get("additional_rate_limits")
    if isinstance(additional, list):
        for item in additional:
            if isinstance(item, dict):
                rate_limit = item.get("rate_limit")
                candidates.append(rate_limit if isinstance(rate_limit, dict) else item)
    if window_minutes_from(raw) is not None or raw.get("used_percent") is not None:
        candidates.append(raw)
    return candidates


def normalize_rate_limits(raw: dict[str, Any], now: float | None = None) -> dict[str, dict[str, Any]]:
    windows = {
        "five_hour": empty_window() | {"label": tr("window_5h")},
        "weekly": empty_window() | {"label": tr("window_7d")},
    }
    for item in candidate_windows(raw):
        minutes = window_minutes_from(item)
        if minutes == FIVE_HOUR_MINUTES:
            normalized = normalize_window(item, tr("window_5h"), now=now)
            if normalized:
                windows["five_hour"] = normalized
        elif minutes == WEEKLY_MINUTES:
            normalized = normalize_window(item, tr("window_7d"), now=now)
            if normalized:
                windows["weekly"] = normalized

    if not windows["five_hour"]["available"]:
        primary = raw.get("primary") or raw.get("primary_window")
        primary_minutes = window_minutes_from(primary) if isinstance(primary, dict) else None
        if isinstance(primary, dict) and primary_minutes in (None, FIVE_HOUR_MINUTES):
            normalized = normalize_window(primary, tr("window_5h"), now=now)
            if normalized:
                normalized["window_minutes"] = normalized["window_minutes"] or FIVE_HOUR_MINUTES
                windows["five_hour"] = normalized
        elif primary_minutes == WEEKLY_MINUTES:
            windows["five_hour"]["not_offered"] = True
    if not windows["weekly"]["available"]:
        secondary = raw.get("secondary") or raw.get("secondary_window")
        secondary_minutes = window_minutes_from(secondary) if isinstance(secondary, dict) else None
        if isinstance(secondary, dict) and secondary_minutes in (None, WEEKLY_MINUTES):
            normalized = normalize_window(secondary, tr("window_7d"), now=now)
            if normalized:
                normalized["window_minutes"] = normalized["window_minutes"] or WEEKLY_MINUTES
                windows["weekly"] = normalized
    return windows


def sample_has_windows(sample: dict[str, Any]) -> bool:
    windows = sample.get("windows")
    if not isinstance(windows, dict):
        return False
    return any(isinstance(item, dict) and item.get("available") for item in windows.values())


class CodexRateLimitReader:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.codex_home = codex_home_from_config(config)

    def read(self) -> dict[str, Any]:
        sample = empty_sample(self.config)
        plan = read_local_plan_metadata(self.codex_home)
        sample["plan_type"] = plan.get("plan_type")
        sample["plan_expires_at"] = plan.get("plan_expires_at")
        sample["plan_checked_at"] = plan.get("plan_checked_at")
        latest = self._find_latest_rate_limits()
        if latest is None:
            sample["errors"].append(tr("note_no_snapshot"))
            sample["note"] = tr("note_new_record")
            return sample

        raw = latest["rate_limits"]
        windows = normalize_rate_limits(raw)
        sample["windows"] = windows
        sample["ok"] = sample_has_windows(sample)
        sample["source_state"] = "live" if sample["ok"] else "unavailable"
        sample["source_event_at"] = latest.get("timestamp")
        sample["source_path"] = str(latest.get("path"))
        sample["plan_type"] = raw.get("plan_type") or sample.get("plan_type")
        credit_resets = resets_from_credits(raw)
        if credit_resets is not None:
            sample["resets_remaining"] = credit_resets
            sample["resets_source"] = "credits"
        else:
            sample["resets_remaining"] = resets_before_expiry(
                windows.get("weekly", {}).get("reset_at"),
                sample.get("plan_expires_at"),
                now=sample.get("snapshot_at"),
            )
            sample["resets_source"] = "estimate" if sample["resets_remaining"] is not None else None
        sample["limit_id"] = raw.get("limit_id")
        sample["rate_limit_reached_type"] = raw.get("rate_limit_reached_type")
        stale_count = sum(1 for item in windows.values() if item.get("available") and item.get("stale"))
        if not sample["ok"]:
            sample["errors"].append(tr("note_unrecognized"))
            sample["note"] = tr("note_format_changed")
        elif stale_count:
            sample["note"] = tr("note_stale")
        else:
            sample["note"] = tr("note_local")
        return sample

    def _find_latest_rate_limits(self) -> dict[str, Any] | None:
        logs_candidate = self._find_latest_rate_limits_in_logs()
        sessions_candidate = self._find_latest_rate_limits_in_sessions(
            newer_than=float(logs_candidate.get("timestamp") or 0) if logs_candidate else 0.0
        )
        candidates = [item for item in (logs_candidate, sessions_candidate) if item is not None]
        if not candidates:
            return None
        return max(candidates, key=lambda item: float(item.get("timestamp") or 0))

    def _find_latest_rate_limits_in_sessions(self, newer_than: float = 0.0) -> dict[str, Any] | None:
        sessions = self.codex_home / "sessions"
        if not sessions.exists():
            return None
        files_with_mtime: list[tuple[float, pathlib.Path]] = []
        for path in sessions.rglob("*.jsonl"):
            if not path.is_file():
                continue
            with contextlib.suppress(OSError):
                mtime = path.stat().st_mtime
                if mtime + 1.0 >= newer_than:
                    files_with_mtime.append((mtime, path))
        files_with_mtime.sort(reverse=True)
        best: dict[str, Any] | None = None
        best_ts = newer_than
        for mtime, path in files_with_mtime[:MAX_SESSION_FILES]:
            try:
                with path.open("rb") as handle:
                    size = handle.seek(0, os.SEEK_END)
                    start = max(0, size - SESSION_TAIL_BYTES)
                    handle.seek(start)
                    chunk = handle.read()
                if start:
                    newline = chunk.find(b"\n")
                    chunk = chunk[newline + 1:] if newline >= 0 else b""
                for raw_line in reversed(chunk.splitlines()):
                    if b'"rate_limit' not in raw_line:
                        continue
                    try:
                        event = json.loads(raw_line.decode("utf-8", errors="replace"))
                    except Exception:
                        continue
                    event_ts = parse_event_timestamp(event.get("timestamp")) or mtime
                    if event_ts < best_ts:
                        continue
                    found_in_line = False
                    for raw in iter_rate_limit_payloads(event):
                        windows = normalize_rate_limits(raw)
                        if not any(item.get("available") for item in windows.values()):
                            continue
                        best_ts = event_ts
                        best = {"timestamp": event_ts, "path": path, "rate_limits": raw}
                        found_in_line = True
                        break
                    if found_in_line:
                        break
            except Exception as exc:
                log_line(f"Failed to inspect {path}: {exc}")
        return best

    def _connect_sqlite_ro(self, path: pathlib.Path) -> sqlite3.Connection:
        uri = path.resolve().as_uri() + "?mode=ro&cache=shared"
        con = sqlite3.connect(uri, uri=True, timeout=0.75)
        con.row_factory = sqlite3.Row
        with contextlib.suppress(Exception):
            con.execute("pragma query_only = true")
        return con

    def _find_latest_rate_limits_in_logs(self) -> dict[str, Any] | None:
        db = self.codex_home / "logs_2.sqlite"
        if not db.exists():
            return None
        try:
            con = self._connect_sqlite_ro(db)
            try:
                rows = con.execute(
                    """
                    select id, ts, ts_nanos, feedback_log_body
                    from logs
                    where target = 'codex_api::endpoint::responses_websocket'
                      and feedback_log_body like '%websocket event:%'
                      and feedback_log_body like '%codex.rate_limits%'
                    order by ts desc, ts_nanos desc
                    limit 200
                    """
                ).fetchall()
            finally:
                con.close()
        except Exception as exc:
            log_line(f"Failed to inspect logs_2.sqlite: {exc}")
            return None

        decoder = json.JSONDecoder()
        marker = "websocket event: "
        for row in rows:
            body = str(row["feedback_log_body"] or "")
            idx = body.find(marker)
            if idx < 0:
                continue
            try:
                event, _end = decoder.raw_decode(body[idx + len(marker):].strip())
            except Exception:
                continue
            if not isinstance(event, dict) or event.get("type") != "codex.rate_limits":
                continue
            rate_limits = event.get("rate_limits")
            if not isinstance(rate_limits, dict):
                continue
            raw = dict(rate_limits)
            raw.setdefault("limit_id", "codex")
            raw.setdefault("plan_type", event.get("plan_type"))
            if "limit_reached" in rate_limits:
                raw.setdefault("rate_limit_reached_type", "primary" if rate_limits.get("limit_reached") else None)
            if not any(item.get("available") for item in normalize_rate_limits(raw).values()):
                continue
            return {
                "timestamp": float(row["ts"] or 0),
                "path": f"{db}#logs:{row['id']}",
                "rate_limits": raw,
            }
        return None


def read_snapshot(
    config: dict[str, Any] | None = None,
    cache: bool = True,
    cache_path: pathlib.Path = CACHE_PATH,
) -> dict[str, Any]:
    config = load_config() if config is None else config
    try:
        sample = CodexRateLimitReader(config).read()
        if sample.get("ok"):
            if cache:
                atomic_write_json(cache_path, sample)
            return sample

        cached = load_json(cache_path, None)
        if isinstance(cached, dict) and cached.get("version") == APP_VERSION and sample_has_windows(cached):
            cached = dict(cached)
            cached["source_state"] = "cache"
            cached["snapshot_at"] = now_ts()
            cached["errors"] = sample.get("errors", [])
            cached["note"] = tr("note_cache_no_new")
            return cached
        return sample
    except Exception as exc:
        log_line("Snapshot read crashed:\n" + traceback.format_exc())
        cached = load_json(cache_path, None)
        if isinstance(cached, dict) and cached.get("version") == APP_VERSION and sample_has_windows(cached):
            cached = dict(cached)
            cached["source_state"] = "cache"
            cached["snapshot_at"] = now_ts()
            cached["errors"] = [tr("note_cache_fallback", error=exc)]
            cached["note"] = tr("note_cache")
            return cached
        sample = empty_sample(config)
        sample["errors"].append(str(exc))
        sample["note"] = tr("note_failed")
        return sample


def set_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    with contextlib.suppress(Exception):
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    with contextlib.suppress(Exception):
        ctypes.windll.user32.SetProcessDPIAware()


class AccentPolicy(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_int),
    ]


class WindowCompositionAttributeData(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t),
    ]


def rgba_to_abgr(red: int, green: int, blue: int, alpha: int) -> int:
    return ((alpha & 0xFF) << 24) | ((blue & 0xFF) << 16) | ((green & 0xFF) << 8) | (red & 0xFF)


def windows_toplevel_handle(root: tk.Tk) -> int | None:
    if sys.platform != "win32":
        return None
    try:
        root.update_idletasks()
        hwnd = int(root.winfo_id())
        user32 = ctypes.windll.user32
        user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        user32.GetAncestor.restype = ctypes.c_void_p
        top_hwnd = user32.GetAncestor(ctypes.c_void_p(hwnd), 2)  # GA_ROOT
        return int(top_hwnd or hwnd)
    except Exception:
        return None


def apply_windows_glass(root: tk.Tk) -> bool:
    if sys.platform != "win32":
        return False
    applied = False
    try:
        root.update_idletasks()
        hwnd = windows_toplevel_handle(root)
        if hwnd is None:
            return False
    except Exception:
        return False

    with contextlib.suppress(Exception):
        value = ctypes.c_int(2)  # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(value), ctypes.sizeof(value))

    with contextlib.suppress(Exception):
        value = ctypes.c_int(3)  # DWMSBT_TRANSIENTWINDOW, acrylic-like on Windows 11
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(value), ctypes.sizeof(value))
        applied = applied or result == 0

    with contextlib.suppress(Exception):
        accent = AccentPolicy()
        accent.AccentState = 4  # ACCENT_ENABLE_ACRYLICBLURBEHIND
        accent.AccentFlags = 2
        accent.GradientColor = rgba_to_abgr(8, 13, 24, 210)
        data = WindowCompositionAttributeData()
        data.Attribute = 19  # WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)
        result = ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
        applied = applied or bool(result)
    return applied


def apply_windows_native_corners(root: tk.Tk) -> bool:
    if sys.platform != "win32":
        return False
    hwnd = windows_toplevel_handle(root)
    if hwnd is None:
        return False
    rounded = False
    with contextlib.suppress(Exception):
        value = ctypes.c_int(2)  # DWMWCP_ROUND
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), 33, ctypes.byref(value), ctypes.sizeof(value)
        )
        rounded = result == 0
    with contextlib.suppress(Exception):
        border = ctypes.c_uint(0xFFFFFFFE)  # DWMWA_COLOR_NONE
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), 34, ctypes.byref(border), ctypes.sizeof(border)
        )
    with contextlib.suppress(Exception):
        policy = ctypes.c_int(1)  # DWMNCRP_DISABLED; removes the borderless-window shadow.
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), 2, ctypes.byref(policy), ctypes.sizeof(policy)
        )
    return rounded


def apply_rounded_window_region(root: tk.Tk, width: int, height: int, radius: int) -> bool:
    if sys.platform != "win32":
        return False
    try:
        root.update_idletasks()
        hwnd = windows_toplevel_handle(root)
        if hwnd is None:
            return False
        diameter = max(2, int(radius * 2))
        region = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, int(width) + 1, int(height) + 1, diameter, diameter)
        if not region:
            return False
        result = ctypes.windll.user32.SetWindowRgn(hwnd, region, True)
        return bool(result)
    except Exception as exc:
        log_line(f"Failed to apply rounded window region: {exc}")
        return False


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if ImageFont is None:
        raise RuntimeError("Pillow is unavailable")
    windir = pathlib.Path(os.environ.get("WINDIR", r"C:\Windows"))
    mac_fonts = pathlib.Path("/System/Library/Fonts")
    mac_supplemental = pathlib.Path("/System/Library/Fonts/Supplemental")
    candidates = [
        mac_fonts / ("PingFang.ttc"),
        mac_supplemental / ("Arial Unicode.ttf"),
        mac_supplemental / ("Arial Bold.ttf" if bold else "Arial.ttf"),
        pathlib.Path("/Library/Fonts") / ("Arial Unicode.ttf"),
        windir / "Fonts" / ("msyhbd.ttc" if bold else "msyh.ttc"),
        windir / "Fonts" / ("segoeuib.ttf" if bold else "segoeui.ttf"),
        windir / "Fonts" / ("arialbd.ttf" if bold else "arial.ttf"),
    ]
    for path in candidates:
        with contextlib.suppress(Exception):
            if path.exists():
                return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def load_display_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if ImageFont is None:
        raise RuntimeError("Pillow is unavailable")
    windir = pathlib.Path(os.environ.get("WINDIR", r"C:\Windows"))
    mac_fonts = pathlib.Path("/System/Library/Fonts")
    candidates = [
        mac_fonts / ("SFNS.ttf"),
        mac_fonts / ("SFNSDisplay.ttf"),
        windir / "Fonts" / ("seguisb.ttf" if bold else "SegUIVar.ttf"),
        windir / "Fonts" / ("segoeuib.ttf" if bold else "segoeui.ttf"),
    ]
    for path in candidates:
        with contextlib.suppress(Exception):
            if path.exists():
                return ImageFont.truetype(str(path), size=size)
    return load_font(size, bold=bold)


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    suffix: str = "...",
) -> str:
    if text_width(draw, text, font) <= max_width:
        return text
    trimmed = text
    while trimmed and text_width(draw, trimmed + suffix, font) > max_width:
        trimmed = trimmed[:-1]
    return (trimmed + suffix) if trimmed else suffix


def percent_text(value: Any) -> str:
    numeric = clean_float(value)
    if numeric is None:
        return "--%"
    if abs(numeric - round(numeric)) < 0.05:
        return f"{int(round(numeric))}%"
    return f"{numeric:.1f}%"


def health_color(remaining: Any) -> str:
    value = clean_float(remaining)
    if value is None:
        return "#8E8E93"
    if value >= 60:
        return "#34C759"
    if value >= 25:
        return "#007AFF"
    if value >= 12:
        return "#FF9500"
    return "#FF3B30"


class CardRenderer:
    WIDTH = 304
    HEIGHT = 536
    SCALE = 2
    KEY = "#010203"

    def __init__(self) -> None:
        if Image is None or ImageDraw is None or ImageFilter is None:
            raise RuntimeError("Pillow is unavailable")
        self._panel_surfaces: dict[tuple[bool, bool], Image.Image] = {}
        self.glass_panel = self._load_glass_panel()
        self.codex_mark = self._load_codex_mark()

    def _load_glass_panel(self) -> Image.Image | None:
        if Image is None or not GLASS_PANEL_PATH.exists():
            return None
        try:
            panel = Image.open(GLASS_PANEL_PATH).convert("RGBA")
            expected = (self.WIDTH * self.SCALE, self.HEIGHT * self.SCALE)
            if panel.size != expected:
                panel = panel.resize(expected, Image.Resampling.LANCZOS)
            return panel
        except Exception as exc:
            log_line(f"Failed to load Image-2 glass panel: {exc}")
            return None

    def _load_codex_mark(self) -> Image.Image | None:
        if Image is None or not WIDGET_MARK_PATH.exists():
            return None
        try:
            icon = Image.open(WIDGET_MARK_PATH).convert("RGBA")
            canvas_size = self.sc(40)
            art_size = self.sc(38)
            art = icon.resize((art_size, art_size), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
            canvas.alpha_composite(art, ((canvas_size - art_size) // 2, (canvas_size - art_size) // 2))
            return canvas
        except Exception as exc:
            log_line(f"Failed to load Codex mark: {exc}")
            return None

    def sc(self, value: float) -> int:
        return int(round(value * self.SCALE))

    def xy(self, *values: float) -> tuple[int, ...]:
        return tuple(self.sc(value) for value in values)

    def render_rgba(self, sample: dict[str, Any] | None, hover: bool = False) -> Image.Image:
        return self._render_surface(sample, hover=hover, native=False)

    def _render_surface(
        self,
        sample: dict[str, Any] | None,
        hover: bool,
        native: bool,
    ) -> Image.Image:
        sample = empty_sample() if sample is None else sample
        scale = self.SCALE
        width, height = self.WIDTH * scale, self.HEIGHT * scale
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        image = self._paint_acrylic_panel(image, hover=hover, native=native)
        draw = ImageDraw.Draw(image)

        self._draw_header(image, draw, sample)
        self._draw_week_limit(image, draw, sample)
        self._draw_account_info(draw, sample)
        self._draw_footer(draw, sample)

        rendered = image.resize((self.WIDTH, self.HEIGHT), Image.Resampling.LANCZOS)
        return rendered if native else self._apply_window_corner_alpha(rendered)

    def render(self, sample: dict[str, Any] | None, hover: bool = False) -> Image.Image:
        rgba = self.render_rgba(sample, hover=hover)
        background = Image.new("RGB", rgba.size, self.KEY)
        binary_alpha = rgba.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
        background.paste(rgba.convert("RGB"), (0, 0), binary_alpha)
        return background

    def render_native(self, sample: dict[str, Any] | None, hover: bool = False) -> Image.Image:
        return self._render_surface(sample, hover=hover, native=True).convert("RGB")

    def _apply_window_corner_alpha(self, image: Image.Image) -> Image.Image:
        oversample = 4
        mask_size = (image.size[0] * oversample, image.size[1] * oversample)
        mask = Image.new("L", mask_size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle(
            (0, 0, mask_size[0] - 1, mask_size[1] - 1),
            radius=28 * oversample,
            fill=255,
        )
        mask = mask.resize(image.size, Image.Resampling.LANCZOS)
        alpha = image.getchannel("A")
        if ImageChops is not None:
            alpha = ImageChops.multiply(alpha, mask)
        else:
            alpha = Image.composite(alpha, Image.new("L", image.size, 0), mask)
        result = image.copy()
        result.putalpha(alpha)
        return result

    def _paint_acrylic_panel(
        self,
        image: Image.Image,
        hover: bool = False,
        native: bool = False,
    ) -> Image.Image:
        cache_key = (hover, native)
        cached = self._panel_surfaces.get(cache_key)
        if cached is not None:
            return Image.alpha_composite(image, cached)

        if self.glass_panel is not None:
            panel = self.glass_panel.copy()
            if native:
                inset = self.sc(20)
                panel = panel.crop((inset, inset, panel.width - inset, panel.height - inset))
                panel = panel.resize(self.glass_panel.size, Image.Resampling.LANCZOS)
                panel.putalpha(255)
            if hover:
                glass_lift = Image.new("RGBA", panel.size, (154, 174, 188, 18))
                panel = Image.alpha_composite(panel, glass_lift)
            self._panel_surfaces[cache_key] = panel.copy()
            return Image.alpha_composite(image, panel)

        width, height = image.size
        panel = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        panel_draw = ImageDraw.Draw(panel)
        for y in range(height):
            ratio = y / max(1, height - 1)
            top = (36, 41, 48) if hover else (30, 35, 41)
            bottom = (18, 23, 29) if hover else (15, 20, 25)
            red = int(top[0] + (bottom[0] - top[0]) * ratio)
            green = int(top[1] + (bottom[1] - top[1]) * ratio)
            blue = int(top[2] + (bottom[2] - top[2]) * ratio)
            panel_draw.line((0, y, width, y), fill=(red, green, blue, 255))

        lighting = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        light_draw = ImageDraw.Draw(lighting)
        light_draw.ellipse(
            (-self.sc(70), -self.sc(135), self.sc(360), self.sc(175)),
            fill=(218, 226, 233, 20 if hover else 12),
        )
        light_draw.ellipse(
            (self.sc(176), -self.sc(95), self.sc(430), self.sc(320)),
            fill=(132, 169, 192, 88 if hover else 72),
        )
        light_draw.ellipse(
            (self.sc(220), self.sc(80), self.sc(430), self.sc(570)),
            fill=(105, 136, 158, 58 if hover else 45),
        )
        light_draw.ellipse(
            (self.sc(22), self.sc(105), self.sc(250), self.sc(455)),
            fill=(0, 0, 0, 54 if hover else 62),
        )
        lighting = lighting.filter(ImageFilter.GaussianBlur(self.sc(54)))
        panel = Image.alpha_composite(panel, lighting)

        edge_glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        edge_draw = ImageDraw.Draw(edge_glow)
        edge_draw.rounded_rectangle(
            (self.sc(5), self.sc(5), width - self.sc(5), height - self.sc(5)),
            radius=self.sc(24),
            outline=(170, 181, 190, 178 if hover else 150),
            width=self.sc(18),
        )
        edge_glow = edge_glow.filter(ImageFilter.GaussianBlur(self.sc(14)))
        panel = Image.alpha_composite(panel, edge_glow)

        rim = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        rim_draw = ImageDraw.Draw(rim)
        rim_draw.rounded_rectangle(
            (self.sc(1), self.sc(1), width - self.sc(1) - 1, height - self.sc(1) - 1),
            radius=self.sc(27),
            outline=(177, 190, 200, 88 if hover else 68),
            width=self.sc(1),
        )
        rim_draw.rounded_rectangle(
            (self.sc(3), self.sc(3), width - self.sc(3) - 1, height - self.sc(3) - 1),
            radius=self.sc(25),
            outline=(240, 245, 249, 18 if hover else 11),
            width=1,
        )
        rim_draw.line(
            (self.sc(28), self.sc(2), width - self.sc(28), self.sc(2)),
            fill=(225, 234, 241, 65 if hover else 45),
            width=1,
        )
        rim_draw.line(
            (width - self.sc(2), self.sc(28), width - self.sc(2), self.sc(250)),
            fill=(190, 208, 220, 60 if hover else 40),
            width=1,
        )
        panel = Image.alpha_composite(panel, rim)

        noise = Image.effect_noise((width, height), 8).convert("L")
        noise_alpha = noise.point(lambda value: (6 if hover else 4) if value > 142 else 0)
        noise_layer = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        noise_layer.putalpha(noise_alpha)
        panel = Image.alpha_composite(panel, noise_layer)
        self._panel_surfaces[cache_key] = panel.copy()
        return Image.alpha_composite(image, panel)

    def _font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        return load_font(self.sc(size), bold=bold)

    def _display_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        return load_display_font(self.sc(size), bold=bold)

    def _draw_gradient_text(
        self,
        image: Image.Image,
        position: tuple[int, int],
        text: str,
        font: ImageFont.ImageFont,
        top: str,
        bottom: str,
        vertical_scale: float = 1.0,
    ) -> None:
        mask = Image.new("L", image.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.text(self.xy(*position), text, font=font, fill=255)
        bounds = mask.getbbox()
        if bounds is None:
            return
        if abs(vertical_scale - 1.0) > 0.01:
            glyph = mask.crop(bounds)
            stretched_height = max(1, int(round(glyph.height * vertical_scale)))
            glyph = glyph.resize((glyph.width, stretched_height), Image.Resampling.LANCZOS)
            mask = Image.new("L", image.size, 0)
            mask.paste(glyph, (bounds[0], bounds[1]))
            bounds = mask.getbbox()
            if bounds is None:
                return

        glow_alpha = mask.filter(ImageFilter.GaussianBlur(self.sc(5))).point(lambda value: int(value * 0.15))
        glow = Image.new("RGBA", image.size, self._hex_rgba(bottom, 0))
        glow.putalpha(glow_alpha)
        image.alpha_composite(glow)

        top_rgb = self._hex_rgb(top)
        bottom_rgb = self._hex_rgb(bottom)
        gradient = Image.new("RGBA", image.size, (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)
        y1, y2 = bounds[1], max(bounds[1] + 1, bounds[3] - 1)
        for y in range(y1, y2 + 1):
            ratio = (y - y1) / max(1, y2 - y1)
            color = tuple(int(top_rgb[index] + (bottom_rgb[index] - top_rgb[index]) * ratio) for index in range(3))
            gradient_draw.line((bounds[0], y, bounds[2], y), fill=(*color, 255))
        gradient.putalpha(mask)
        image.alpha_composite(gradient)

    @staticmethod
    def _hex_rgb(color: str) -> tuple[int, int, int]:
        value = color.lstrip("#")
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))

    @classmethod
    def _hex_rgba(cls, color: str, alpha: int) -> tuple[int, int, int, int]:
        return (*cls._hex_rgb(color), alpha)

    def _draw_header(self, image: Image.Image, draw: ImageDraw.ImageDraw, sample: dict[str, Any]) -> None:
        ink = "#F8FAFC"
        muted = "#8E9AA8"
        self._draw_codex_mark(image, draw, 39, 47)

        draw.text(self.xy(76, 28), "Codex Limit", font=self._display_font(19, True), fill=ink)
        draw.text(self.xy(76, 53), tr("subtitle"), font=self._font(10, True), fill=muted)
        pill_text = self._status_text(sample)
        status_color = self._status_color(sample)
        pill_width = min(112, max(62, int(text_width(draw, pill_text, self._font(10, True)) / self.SCALE) + 34))
        pill_x2 = 286
        pill_x1 = pill_x2 - pill_width
        draw.rounded_rectangle(
            self.xy(pill_x1, 76, pill_x2, 99),
            radius=self.sc(12),
            fill="#31433F",
            outline="#526A65",
            width=self.sc(1),
        )
        draw.ellipse(self.xy(pill_x1 + 11, 83, pill_x1 + 19, 91), fill=status_color)
        draw.text(self.xy(pill_x1 + 27, 81), pill_text, font=self._font(10, True), fill="#EDF3F5")

        self._draw_refresh_control(draw, 228, 46)
        self._draw_close_control(draw, 271, 46)

    def _status_text(self, sample: dict[str, Any]) -> str:
        if sample.get("refreshing"):
            return tr("status_refreshing")
        if sample.get("usage_changed"):
            return tr("status_updated")
        if sample.get("refresh_result") == "unchanged":
            return tr("status_unchanged")
        if sample.get("source_state") == "cache":
            return tr("status_cache")
        if not sample.get("ok"):
            return tr("status_waiting")
        windows = sample.get("windows") or {}
        return tr("status_live")

    def _status_color(self, sample: dict[str, Any]) -> str:
        text = self._status_text(sample)
        if text == tr("status_refreshing"):
            return "#2563EB"
        if text in (tr("status_live"), tr("status_updated")):
            return "#34C759"
        if text in (tr("status_cache"), tr("status_stale"), tr("status_unchanged")):
            return "#FF9500"
        return "#FF3B30"

    def _draw_refresh_icon(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str) -> None:
        # Based on the standard 24x24 refresh-cw structure used by Lucide/Feather:
        # two circular strokes with arrow corners instead of a detached arrowhead.
        scale = 0.72
        stroke = 1.55

        def p(x: float, y: float) -> tuple[float, float]:
            return cx + (x - 12) * scale, cy + (y - 12) * scale

        arc_box = self.xy(cx - 9 * scale, cy - 9 * scale, cx + 9 * scale, cy + 9 * scale)
        draw.arc(arc_box, start=187, end=319, fill=color, width=self.sc(stroke))
        draw.arc(arc_box, start=7, end=139, fill=color, width=self.sc(stroke))
        self._rounded_polyline(draw, [p(18.8, 5.7), p(21, 8), p(16, 8)], color, stroke)
        self._rounded_polyline(draw, [p(5.2, 18.3), p(3, 16), p(8, 16)], color, stroke)

    def _draw_close_icon(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str) -> None:
        draw.line([self.xy(cx - 4, cy - 4), self.xy(cx + 4, cy + 4)], fill=color, width=self.sc(1.6))
        draw.line([self.xy(cx + 4, cy - 4), self.xy(cx - 4, cy + 4)], fill=color, width=self.sc(1.6))

    def _draw_calendar_icon(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str) -> None:
        draw.rounded_rectangle(self.xy(cx - 7, cy - 6, cx + 7, cy + 7), radius=self.sc(3), outline=color, width=self.sc(1.4))
        draw.line(self.xy(cx - 7, cy - 2, cx + 7, cy - 2), fill=color, width=self.sc(1.2))
        draw.line(self.xy(cx - 4, cy - 8, cx - 4, cy - 4), fill=color, width=self.sc(1.5))
        draw.line(self.xy(cx + 4, cy - 8, cx + 4, cy - 4), fill=color, width=self.sc(1.5))
        draw.ellipse(self.xy(cx - 1, cy + 1, cx + 1, cy + 3), fill=color)

    def _draw_clock_icon(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str) -> None:
        draw.ellipse(self.xy(cx - 6, cy - 6, cx + 6, cy + 6), outline=color, width=self.sc(1.2))
        draw.line(self.xy(cx, cy, cx, cy - 3), fill=color, width=self.sc(1.2))
        draw.line(self.xy(cx, cy, cx + 3, cy + 2), fill=color, width=self.sc(1.2))

    def _rounded_polyline(self, draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], color: str, width: float) -> None:
        scaled_width = self.sc(width)
        for start, end in zip(points, points[1:]):
            draw.line([self.xy(*start), self.xy(*end)], fill=color, width=scaled_width)
        radius = width / 2
        for x, y in points:
            draw.ellipse(self.xy(x - radius, y - radius, x + radius, y + radius), fill=color)

    def _draw_refresh_control(self, draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
        fill = "#35414B" if sys.platform != "darwin" else "#303741"
        outline = "#6A7A88"
        draw.ellipse(self.xy(cx - 16, cy - 16, cx + 16, cy + 16), fill=fill, outline=outline, width=self.sc(1))
        draw.arc(self.xy(cx - 14, cy - 14, cx + 14, cy + 14), 205, 330, fill="#A4B2BF", width=self.sc(1))
        self._draw_refresh_icon(draw, cx, cy, "#F0F4F8")

    def _draw_close_control(self, draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
        if sys.platform == "darwin":
            draw.ellipse(self.xy(cx - 10, cy - 10, cx + 10, cy + 10), fill="#FF5F57")
            draw.ellipse(self.xy(cx - 10, cy - 10, cx + 10, cy + 10), outline="#D64D47", width=self.sc(1))
            draw.line([self.xy(cx - 3, cy - 3), self.xy(cx + 3, cy + 3)], fill="#7A1F1A", width=self.sc(1.15))
            draw.line([self.xy(cx + 3, cy - 3), self.xy(cx - 3, cy + 3)], fill="#7A1F1A", width=self.sc(1.15))
            return
        draw.ellipse(self.xy(cx - 16, cy - 16, cx + 16, cy + 16), fill="#35414B", outline="#6A7A88", width=self.sc(1))
        draw.arc(self.xy(cx - 14, cy - 14, cx + 14, cy + 14), 205, 330, fill="#A4B2BF", width=self.sc(1))
        self._draw_close_icon(draw, cx, cy, "#F0F4F8")

    def _draw_codex_mark(self, image: Image.Image, draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
        if self.codex_mark is not None:
            image.alpha_composite(self.codex_mark, dest=self.xy(cx - 20, cy - 20))
            return
        draw.rounded_rectangle(self.xy(cx - 21, cy - 21, cx + 21, cy + 21), radius=self.sc(11), fill="#0B1220")
        draw.rounded_rectangle(self.xy(cx - 20, cy - 20, cx + 20, cy + 20), radius=self.sc(10), outline="#263B5A", width=self.sc(1))
        points = [
            ((cx - 3, cy - 12), (cx + 9, cy - 6)),
            ((cx + 9, cy - 6), (cx + 10, cy + 7)),
            ((cx + 10, cy + 7), (cx - 2, cy + 13)),
            ((cx - 2, cy + 13), (cx - 13, cy + 5)),
            ((cx - 13, cy + 5), (cx - 10, cy - 8)),
            ((cx - 10, cy - 8), (cx - 3, cy - 12)),
        ]
        colors = ["#E0F2FE", "#BFDBFE", "#DBEAFE", "#E0F2FE", "#BFDBFE", "#F8FAFC"]
        for (start, end), color in zip(points, colors):
            self._rounded_line(draw, start, end, color, 4)
        draw.ellipse(self.xy(cx - 4, cy - 4, cx + 4, cy + 4), fill="#0B1220", outline="#E0F2FE", width=self.sc(2))

    def _rounded_line(self, draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str, width: int) -> None:
        scaled_width = self.sc(width)
        draw.line([self.xy(*start), self.xy(*end)], fill=color, width=scaled_width)
        radius = width / 2
        for x, y in (start, end):
            draw.ellipse(self.xy(x - radius, y - radius, x + radius, y + radius), fill=color)

    def _window_style(self, window: dict[str, Any]) -> tuple[str, float, bool, bool]:
        remaining = window.get("remaining_percent")
        available = bool(window.get("available"))
        stale = bool(window.get("stale"))
        if stale:
            return "#94A3B8", 0.0, available, stale
        if not available:
            return "#94A3B8", 0.0, available, stale
        ratio = clamp((clean_float(remaining) or 0.0) / 100.0, 0.0, 1.0)
        value = clean_float(remaining) or 0.0
        if value >= 25:
            return "#73E6A0", ratio, available, stale
        if value >= 12:
            return "#F5C451", ratio, available, stale
        return "#FF6B6B", ratio, available, stale

    def _remaining_label(self, window: dict[str, Any], stale: bool) -> str:
        if stale:
            return "--%"
        if not window.get("available"):
            return "--%"
        return percent_text(window.get("remaining_percent"))

    def _used_label(self, window: dict[str, Any], stale: bool, unavailable: str) -> str:
        if stale:
            return tr("reset_done")
        if not window.get("available"):
            return unavailable
        text = f"{tr('used')} {percent_text(window.get('used_percent'))}"
        delta = clean_float(window.get("used_delta"))
        if delta is not None and abs(delta) >= 0.1:
            arrow = "↑" if delta > 0 else "↓"
            text += f" {arrow}{percent_text(abs(delta))}"
        return text

    def _draw_primary_limit(self, draw: ImageDraw.ImageDraw, sample: dict[str, Any]) -> None:
        window = (sample.get("windows") or {}).get("five_hour") or empty_window()
        color, ratio, available, stale = self._window_style(window)
        if available and not stale:
            color = "#4ADE80"
        x1, y1, x2, y2 = 18, 118, 286, 324
        self._draw_soft_shadow(draw, x1, y1, x2, y2, 24)
        draw.rounded_rectangle(self.xy(x1, y1, x2, y2), radius=self.sc(24), fill="#111C2B")

        draw.text(self.xy(x1 + 22, y1 + 22), "5H", font=self._font(20, True), fill="#F8FAFC")

        not_offered = bool(window.get("not_offered"))
        used_text = self._used_label(window, stale, tr("not_applicable") if not_offered else tr("waiting"))
        used_font = self._font(10, True)
        used_width = min(126, max(84, int(text_width(draw, used_text, used_font) / self.SCALE) + 22))
        draw.rounded_rectangle(self.xy(x2 - used_width - 18, y1 + 21, x2 - 18, y1 + 49), radius=self.sc(11), fill="#2A1F19")
        draw.text(self.xy(x2 - used_width / 2 - 18, y1 + 35), used_text, font=used_font, fill="#FDBA74", anchor="mm")

        main = self._remaining_label(window, stale)
        main_font = self._font(72 if not stale else 40, True)
        draw.text(self.xy(x1 + 22, y1 + 70), main, font=main_font, fill=color)

        reset = self._compact_relative(window.get("reset_at")) if available else tr("model_no_5h") if not_offered else tr("waiting_snapshot")
        if stale:
            reset = tr("stale_snapshot")
        elif available:
            reset = f"{reset}{tr('reset')}"
        draw.text(self.xy(x1 + 24, y1 + 58), reset, font=self._font(13, True), fill="#CBD5E1")

        self._draw_progress(draw, x1 + 22, y2 - 34, x2 - 22, y2 - 18, ratio, color, available and not stale)

    def _draw_week_limit(self, image: Image.Image, draw: ImageDraw.ImageDraw, sample: dict[str, Any]) -> None:
        window = (sample.get("windows") or {}).get("weekly") or empty_window()
        color, ratio, available, stale = self._window_style(window)
        x1, x2 = 40, 280

        self._draw_calendar_icon(draw, 39, 144, "#85919E")
        draw.text(self.xy(57, 132), "7D", font=self._display_font(20, True), fill="#F8FAFC")
        used_text = self._used_label(window, stale, "--")
        used_font = self._font(11, True)
        used_width = min(118, max(74, int(text_width(draw, used_text, used_font) / self.SCALE) + 24))
        draw.rounded_rectangle(
            self.xy(286 - used_width, 130, 286, 158),
            radius=self.sc(14),
            fill="#44342E",
            outline="#64493D",
            width=self.sc(1),
        )
        draw.text(self.xy(286 - used_width / 2, 144), used_text, font=used_font, fill="#FF9A70", anchor="mm")

        main = self._remaining_label(window, stale)
        main_size = 94 if not stale else 48
        main_font = self._display_font(main_size, True)
        while main_size > 60 and text_width(draw, main, main_font) > self.sc(238):
            main_size -= 2
            main_font = self._display_font(main_size, True)
        if color == "#73E6A0":
            gradient_top, gradient_bottom = "#B0F0B9", "#68CA82"
        elif color == "#F5C451":
            gradient_top, gradient_bottom = "#FFE3A3", "#F3B946"
        elif color == "#FF6B6B":
            gradient_top, gradient_bottom = "#FFB2A2", "#FF6B5B"
        else:
            gradient_top, gradient_bottom = "#C5CFDA", "#8492A1"
        self._draw_gradient_text(
            image,
            (42, 153 if not stale else 169),
            main,
            main_font,
            gradient_top,
            gradient_bottom,
            vertical_scale=1.22 if not stale else 1.0,
        )

        reset_core = self._compact_relative(window.get("reset_at")) if available else tr("waiting_snapshot")
        reset_suffix = tr("reset") if available and not stale else ""
        if stale:
            reset_core = tr("stale_snapshot")
        reset_font = self._font(13, True)
        combined_reset = fit_text(draw, f"{reset_core}{reset_suffix}", reset_font, self.sc(240))
        if combined_reset == f"{reset_core}{reset_suffix}" and reset_suffix:
            draw.text(self.xy(x1, 284), reset_core, font=reset_font, fill="#69B8F7")
            reset_x = x1 + text_width(draw, reset_core, reset_font) / self.SCALE
            draw.text(self.xy(reset_x, 284), reset_suffix, font=reset_font, fill="#A0AAB5")
        else:
            draw.text(self.xy(x1, 284), combined_reset, font=reset_font, fill="#8FC9FF" if available and not stale else "#8B98A6")

        self._draw_progress(draw, x1, 315, x2, 329, ratio, color, available and not stale)
        draw.line(self.xy(x1, 355, x2, 355), fill="#3B444C", width=self.sc(1))

    def _draw_account_info(self, draw: ImageDraw.ImageDraw, sample: dict[str, Any]) -> None:
        plan = str(sample.get("plan_type") or "Codex").upper()
        expires_at = clean_float(sample.get("plan_expires_at"))
        resets = clean_int(sample.get("resets_remaining"), 0)

        if expires_at:
            expires = dt.datetime.fromtimestamp(expires_at).astimezone()
            expiry_value = expires.strftime("%m/%d")
            expiry_note = f"{expires.strftime('%H:%M')} · {plan}"
        else:
            expiry_value = "--/--"
            expiry_note = plan

        reset_value = tr("times_left", value=resets) if resets is not None else "--"
        draw.line(self.xy(158, 376, 158, 472), fill="#3B444C", width=self.sc(1))
        reset_note = tr("codex_credits") if sample.get("resets_source") == "credits" else tr("weekly_cycle")
        columns = (
            (40, 148, 47, tr("plan_expires"), expiry_value, expiry_note, "calendar"),
            (188, 280, 195, tr("resets_left"), reset_value, reset_note, "cycle"),
        )
        for x1, x2, icon_x, label, value, note, icon in columns:
            icon_y = 383
            if icon == "calendar":
                self._draw_clock_icon(draw, icon_x, icon_y, "#69B9F5")
            else:
                self._draw_refresh_icon(draw, icon_x, icon_y, "#69DE91")
            draw.text(self.xy(x1, 398), label, font=self._font(11, True), fill="#919CA8")
            value_font = self._font(34, True) if any(ord(char) > 127 for char in value) else self._display_font(34, True)
            value = fit_text(draw, value, value_font, self.sc(x2 - x1), suffix="")
            draw.text(self.xy(x1, 418), value, font=value_font, fill="#F8FAFC")
            note = fit_text(draw, note, self._font(10, True), self.sc(x2 - x1), suffix="")
            draw.text(self.xy(x1, 459), note, font=self._font(10, True), fill="#748291")

    def _draw_progress(self, draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, ratio: float, color: str, active: bool) -> None:
        radius = self.sc((y2 - y1) / 2)
        draw.rounded_rectangle(self.xy(x1, y1, x2, y2), radius=radius, fill="#3A434C")
        if not active:
            fill_x2 = x1 + max(10, int((x2 - x1) * clamp(ratio, 0.0, 1.0)))
            draw.rounded_rectangle(self.xy(x1, y1, fill_x2, y2), radius=radius, fill=color)
            return
        remaining_ratio = clamp(ratio, 0.0, 1.0)
        split_x = x1 + int((x2 - x1) * remaining_ratio)
        if split_x > x1:
            draw.rounded_rectangle(self.xy(x1, y1, split_x, y2), radius=radius, fill=color)
        if split_x < x2:
            draw.rounded_rectangle(self.xy(split_x, y1, x2, y2), radius=radius, fill="#F47C59")
        if x1 < split_x < x2:
            draw.rectangle(self.xy(split_x - 1.5, y1, split_x + 1.5, y2), fill="#171C21")
        draw.line(self.xy(x1 + 7, y1 + 1, x2 - 7, y1 + 1), fill="#A8B4BB", width=1)

    def _draw_soft_shadow(self, draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, radius: int) -> None:
        draw.rounded_rectangle(self.xy(x1 + 2, y1 + 4, x2 + 2, y2 + 5), radius=self.sc(radius), fill="#07101F")

    def _draw_metric_tile(
        self,
        draw: ImageDraw.ImageDraw,
        sample: dict[str, Any],
        key: str,
        box: tuple[int, int, int, int],
        accent: str,
        primary: bool,
    ) -> None:
        x1, y1, x2, y2 = box
        window = (sample.get("windows") or {}).get(key) or empty_window()
        remaining = window.get("remaining_percent")
        used = window.get("used_percent")
        available = bool(window.get("available"))
        stale = bool(window.get("stale"))
        color = "#94A3B8" if not available else health_color(remaining)
        if stale:
            color = "#FF9500"

        draw.rounded_rectangle(self.xy(x1, y1, x2, y2), radius=self.sc(24), fill="#F8FBFF")
        draw.rounded_rectangle(self.xy(x1 + 2, y1 + 2, x2 - 2, y2 - 2), radius=self.sc(22), outline="#FFFFFF", width=self.sc(1))

        label_font = self._font(17 if primary else 15, True)
        small_font = self._font(13 if primary else 12)
        draw.text(self.xy(x1 + 22, y1 + 20), tr("window_5h" if key == "five_hour" else "window_7d"), font=label_font, fill="#0F172A")

        not_offered = bool(window.get("not_offered"))
        used_text = f"{tr('used')} {percent_text(used)}" if available else tr("not_applicable") if not_offered else tr("status_waiting")
        used_w = text_width(draw, used_text, self._font(11, True)) / self.SCALE + 24
        draw.rounded_rectangle(self.xy(x2 - used_w - 20, y1 + 18, x2 - 20, y1 + 43), radius=self.sc(12), fill=self._soft_color(accent))
        draw.text(self.xy(x2 - used_w - 8, y1 + 24), used_text, font=self._font(11, True), fill="#334155")

        if stale:
            main = tr("status_stale")
            main_font = self._font(30 if primary else 22, True)
            reset_line = f"{tr('stale_snapshot')} {percent_text(remaining)}"
            helper_line = tr("waiting_snapshot")
        else:
            main = percent_text(remaining) if available else "--%"
            main_font = self._font(58 if primary else 42, True)
            reset_line = f"{self._compact_relative(window.get('reset_at'))}{tr('reset')}" if available else tr("model_no_5h") if not_offered else tr("waiting_snapshot")
            helper_line = ""

        reset_line = fit_text(draw, reset_line, small_font, self.sc((x2 - x1) - 44))
        draw.text(self.xy(x1 + 24, y1 + 51), reset_line, font=small_font, fill="#64748B")

        value_y = y1 + (75 if primary else 75)
        draw.text(self.xy(x1 + 22, value_y), main, font=main_font, fill=color)
        helper_x = x1 + 22 + (text_width(draw, main, main_font) / self.SCALE) + 10
        if available and not stale and helper_x < x2 - 38:
            draw.text(self.xy(helper_x, value_y + (32 if primary else 22)), helper_line, font=self._font(14 if primary else 12, True), fill="#475569")

        bar_x1, bar_y1, bar_x2, bar_y2 = x1 + 24, y2 - 24, x2 - 24, y2 - 14
        draw.rounded_rectangle(self.xy(bar_x1, bar_y1, bar_x2, bar_y2), radius=self.sc(5), fill="#E3EBF5")
        if available and not stale:
            ratio = clamp((clean_float(remaining) or 0.0) / 100.0, 0.0, 1.0)
            fill_x2 = bar_x1 + max(8, int((bar_x2 - bar_x1) * ratio))
            draw.rounded_rectangle(self.xy(bar_x1, bar_y1, fill_x2, bar_y2), radius=self.sc(5), fill=color)
        elif stale:
            draw.rounded_rectangle(self.xy(bar_x1, bar_y1, bar_x1 + 34, bar_y2), radius=self.sc(5), fill=color)

    def _compact_relative(self, timestamp: Any) -> str:
        text = format_relative(timestamp)
        return text.replace(" ", "") if CURRENT_LANGUAGE == "zh" else text

    def _soft_color(self, color: str) -> str:
        if color == "#34C759":
            return "#E8F8ED"
        if color == "#007AFF":
            return "#E8F2FF"
        return "#EEF2F7"

    def _draw_footer(self, draw: ImageDraw.ImageDraw, sample: dict[str, Any]) -> None:
        source_event = sample.get("source_event_at")
        if sample.get("refreshing"):
            footer = tr("footer_refreshing")
        elif sample.get("refresh_result") == "unchanged":
            footer = tr("footer_unchanged", age=format_age(source_event))
        elif sample.get("usage_changed") and sample.get("primary_delta") is not None:
            delta = float(sample["primary_delta"])
            delta_text = f"{delta:+.1f}".rstrip("0").rstrip(".")
            footer = tr("footer_usage_changed", delta=delta_text)
        elif sample.get("ok"):
            footer = tr("footer_updated", age=format_age(source_event))
        else:
            errors = sample.get("errors") or []
            footer = errors[0] if errors else (sample.get("note") or tr("footer_waiting"))
        if sample.get("source_state") == "cache":
            footer = tr("footer_cache", age=format_age(source_event))
        footer_font = self._font(11, True)
        footer = fit_text(draw, footer, footer_font, self.sc(244))
        footer_width = text_width(draw, footer, footer_font) / self.SCALE
        group_width = footer_width + 19
        start_x = 152 - group_width / 2
        self._draw_clock_icon(draw, int(start_x + 6), 507, "#71808D")
        draw.text(self.xy(start_x + 19, 507), footer, font=footer_font, fill="#8D99A5", anchor="lm")


class UsageWidget:
    WIDTH = CardRenderer.WIDTH
    HEIGHT = CardRenderer.HEIGHT
    KEY = CardRenderer.KEY

    def __init__(
        self,
        root: tk.Tk,
        config: dict[str, Any],
        snapshot_func: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ):
        self.root = root
        self.config = config
        self.snapshot_func = snapshot_func or (lambda cfg: read_snapshot(cfg, cache=True))
        self.renderer = CardRenderer()
        self.queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self.refreshing = False
        self.closed = False
        self.drag_origin: tuple[int, int, int, int] | None = None
        self.drag_moved = False
        self.hovered = False
        self.current_sample: dict[str, Any] | None = None
        self.last_source_stamp: tuple[tuple[str, int, int], ...] | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.native_corners = False
        self._build_window()
        self._make_menu()
        self._place_initial()
        self._apply_window_shape()
        self._set_image(empty_sample(self.config) | {"note": tr("pending_read")})
        self.refresh()
        self._poll_queue()
        self.root.after(int(self.config.get("refresh_seconds", DEFAULT_REFRESH_SECONDS)) * 1000, self._schedule_refresh)
        self._watch_source_changes()
        self._ensure_visible_loop()

    def _build_window(self) -> None:
        self.root.title(tr("app_name"))
        self.root.overrideredirect(True)
        self.root.resizable(False, False)
        self.root.configure(bg=self.KEY)
        self.root.attributes("-topmost", bool(self.config.get("always_on_top", True)))
        with contextlib.suppress(Exception):
            self.root.attributes("-alpha", 1.0)
        if sys.platform != "win32":
            with contextlib.suppress(Exception):
                self.root.wm_attributes("-transparentcolor", self.KEY)
        self.label = tk.Label(self.root, bg=self.KEY, bd=0, highlightthickness=0)
        self.label.pack(fill="both", expand=True)
        self._bind_pointer_events(self.label)
        self.root.bind("<Escape>", lambda _event: self.quit())
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

    def _bind_pointer_events(self, surface: tk.Misc) -> None:
        surface.bind("<ButtonPress-1>", self._begin_drag)
        surface.bind("<B1-Motion>", self._drag)
        surface.bind("<ButtonRelease-1>", self._end_drag)
        surface.bind("<Button-3>", self._show_menu)
        surface.bind("<Enter>", lambda _event: self._set_hovered(True))
        surface.bind("<Leave>", lambda _event: self._set_hovered(False))

    def _make_menu(self) -> None:
        self.menu = tk.Menu(self.root, tearoff=False)
        self.menu.add_command(label=tr("menu_refresh"), command=lambda: self.refresh(force=True))
        self.menu.add_command(label=tr("menu_topmost"), command=self.toggle_topmost)
        self.menu.add_command(label=tr("menu_reset"), command=self.reset_position)
        self.menu.add_separator()
        self.menu.add_command(label=tr("menu_quit"), command=self.quit)

    def _place_initial(self) -> None:
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = self.config.get("window_x")
        y = self.config.get("window_y")
        if x is None or y is None:
            x = sw - self.WIDTH - 34
            y = 58
        x = min(max(8, int(x)), max(8, sw - self.WIDTH - 8))
        y = min(max(8, int(y)), max(8, sh - self.HEIGHT - 48))
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

    def _apply_window_shape(self) -> None:
        if sys.platform == "win32":
            self.native_corners = apply_windows_native_corners(self.root)
            if self.native_corners:
                return
            with contextlib.suppress(Exception):
                self.root.wm_attributes("-transparentcolor", self.KEY)
            apply_windows_glass(self.root)
        apply_rounded_window_region(self.root, self.WIDTH, self.HEIGHT, 28)

    def _set_image(self, sample: dict[str, Any]) -> None:
        self.current_sample = sample
        image = (
            self.renderer.render_native(sample, hover=self.hovered)
            if self.native_corners
            else self.renderer.render(sample, hover=self.hovered)
        )
        next_photo = ImageTk.PhotoImage(image)
        previous_photo = self.photo
        self.label.configure(image=next_photo)
        self.photo = next_photo
        self.label.update_idletasks()
        del previous_photo

    def _set_hovered(self, hovered: bool) -> None:
        if self.hovered == hovered or self.closed:
            return
        self.hovered = hovered
        with contextlib.suppress(Exception):
            self.root.attributes("-alpha", 0.78 if hovered else 1.0)
        if self.current_sample:
            self._set_image(self.current_sample)

    def _begin_drag(self, event: tk.Event) -> None:
        self.drag_origin = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())
        self.drag_moved = False

    def _drag(self, event: tk.Event) -> None:
        if not self.drag_origin:
            return
        sx, sy, wx, wy = self.drag_origin
        dx, dy = event.x_root - sx, event.y_root - sy
        if abs(dx) > 3 or abs(dy) > 3:
            self.drag_moved = True
        self.root.geometry(f"+{wx + dx}+{wy + dy}")

    def _end_drag(self, event: tk.Event) -> None:
        if not self.drag_moved:
            if self._inside(event.x, event.y, 200, 22, 250, 72):
                self.refresh(force=True)
                return
            if self._inside(event.x, event.y, 246, 22, 297, 72):
                self.quit()
                return
        self.config["window_x"] = self.root.winfo_x()
        self.config["window_y"] = self.root.winfo_y()
        save_config(self.config)

    def _inside(self, x: int, y: int, left: int, top: int, right: int, bottom: int) -> bool:
        return left <= x <= right and top <= y <= bottom

    def _show_menu(self, event: tk.Event) -> None:
        self.menu.tk_popup(event.x_root, event.y_root)

    def reset_position(self) -> None:
        sw = self.root.winfo_screenwidth()
        self.config["window_x"] = sw - self.WIDTH - 34
        self.config["window_y"] = 58
        save_config(self.config)
        self._place_initial()
        self._apply_window_shape()

    def toggle_topmost(self) -> None:
        self.config["always_on_top"] = not bool(self.config.get("always_on_top", True))
        self.root.attributes("-topmost", bool(self.config["always_on_top"]))
        save_config(self.config)

    def refresh(self, force: bool = False) -> None:
        if self.refreshing:
            return
        self.refreshing = True
        previous_marker = self._source_marker(self.current_sample)
        if force and self.current_sample:
            pending = dict(self.current_sample)
            pending["refreshing"] = True
            pending["refresh_result"] = None
            pending["note"] = tr("pending_refresh")
            self._set_image(pending)

        def worker() -> None:
            try:
                sample = self.snapshot_func(dict(self.config))
            except Exception:
                log_line("Worker crashed:\n" + traceback.format_exc())
                sample = read_snapshot(dict(self.config), cache=True)
            if force:
                sample["manual_refresh"] = True
                sample["refresh_result"] = "updated" if self._source_marker(sample) != previous_marker else "unchanged"
                if sample["refresh_result"] == "unchanged":
                    sample["note"] = tr("manual_unchanged")
            self.queue.put(sample)

        threading.Thread(target=worker, daemon=True).start()

    def _source_marker(self, sample: dict[str, Any] | None) -> tuple[Any, Any] | None:
        if not sample:
            return None
        return sample.get("source_event_at"), sample.get("source_path")

    def _annotate_usage_changes(self, sample: dict[str, Any]) -> dict[str, Any]:
        previous = self.current_sample
        if not previous or self._source_marker(sample) == self._source_marker(previous):
            return sample
        current_windows = sample.get("windows")
        previous_windows = previous.get("windows")
        if not isinstance(current_windows, dict) or not isinstance(previous_windows, dict):
            return sample

        changed = False
        updated_windows = dict(current_windows)
        for key in ("five_hour", "weekly"):
            current = current_windows.get(key)
            old = previous_windows.get(key)
            if not isinstance(current, dict) or not isinstance(old, dict):
                continue
            current_used = clean_float(current.get("used_percent"))
            previous_used = clean_float(old.get("used_percent"))
            if current_used is None or previous_used is None:
                continue
            delta = round(current_used - previous_used, 1)
            if abs(delta) < 0.1:
                continue
            current = dict(current)
            current["used_delta"] = delta
            updated_windows[key] = current
            changed = True
            if key == "weekly":
                sample["primary_delta"] = delta
        if changed:
            sample["windows"] = updated_windows
            sample["usage_changed"] = True
        return sample

    def _poll_queue(self) -> None:
        try:
            while True:
                sample = self.queue.get_nowait()
                self.refreshing = False
                sample = self._annotate_usage_changes(sample)
                self._set_image(sample)
        except queue.Empty:
            pass
        if not self.closed:
            self.root.after(100, self._poll_queue)

    def _schedule_refresh(self) -> None:
        if self.closed:
            return
        self.refresh()
        self.root.after(int(self.config.get("refresh_seconds", DEFAULT_REFRESH_SECONDS)) * 1000, self._schedule_refresh)

    def _source_files_stamp(self) -> tuple[tuple[str, int, int], ...]:
        codex_home = codex_home_from_config(self.config)
        paths = [codex_home / "logs_2.sqlite", codex_home / "logs_2.sqlite-wal"]
        source_path = str((self.current_sample or {}).get("source_path") or "").split("#", 1)[0]
        if source_path:
            paths.append(pathlib.Path(source_path))
        stamps: list[tuple[str, int, int]] = []
        for path in dict.fromkeys(paths):
            with contextlib.suppress(OSError):
                stat = path.stat()
                stamps.append((str(path), stat.st_mtime_ns, stat.st_size))
        return tuple(stamps)

    def _watch_source_changes(self) -> None:
        if self.closed:
            return
        stamp = self._source_files_stamp()
        if self.last_source_stamp is None:
            self.last_source_stamp = stamp
        elif stamp != self.last_source_stamp:
            self.last_source_stamp = stamp
            self.refresh()
        self.root.after(1000, self._watch_source_changes)

    def _ensure_visible_loop(self) -> None:
        if self.closed:
            return
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x, y = self.root.winfo_x(), self.root.winfo_y()
        if x < -self.WIDTH + 80 or y < -self.HEIGHT + 80 or x > sw - 50 or y > sh - 50:
            self.reset_position()
        self.root.after(7000, self._ensure_visible_loop)

    def quit(self) -> None:
        self.closed = True
        with contextlib.suppress(Exception):
            self.root.destroy()


def create_icon(path: pathlib.Path = ICON_PATH) -> pathlib.Path:
    if Image is None or ImageDraw is None:
        raise RuntimeError("Pillow is unavailable")
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    sizes = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)]
    if SPYGLASS_BASE_PATH.exists():
        icon = Image.open(SPYGLASS_BASE_PATH).convert("RGBA")
        crop_size = min(icon.size)
        left = (icon.width - crop_size) // 2
        top = (icon.height - crop_size) // 2
        icon = icon.crop((left, top, left + crop_size, top + crop_size))
        art = icon.resize((232, 232), Image.Resampling.LANCZOS)
        art = art.filter(ImageFilter.UnsharpMask(radius=0.8, percent=145, threshold=2))
        icon = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        icon.alpha_composite(art, (12, 12))
        frames: list[Image.Image] = []
        for width, height in sizes:
            frame = icon.resize((width, height), Image.Resampling.LANCZOS)
            alpha = frame.getchannel("A")
            alpha_draw = ImageDraw.Draw(alpha)
            alpha_draw.rectangle((0, 0, width - 1, height - 1), outline=0, width=1)
            frame.putalpha(alpha)
            frames.append(frame)
        frames[-1].save(path, format="ICO", sizes=sizes, append_images=frames[:-1])
        return path

    size = 1024
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    def add_mask(mask: Image.Image, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> None:
        gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        px = gradient.load()
        for y in range(size):
            t = y / (size - 1)
            color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3)) + (255,)
            for x in range(size):
                px[x, y] = color
        gradient.putalpha(mask)
        icon.alpha_composite(gradient)

    def rounded_line(
        layer: Image.Image,
        points: list[tuple[int, int]],
        width: int,
        fill: tuple[int, int, int, int],
        outline: tuple[int, int, int, int] | None = None,
        outline_width: int = 0,
    ) -> None:
        draw = ImageDraw.Draw(layer)
        if outline and outline_width:
            draw.line(points, fill=outline, width=width + outline_width * 2, joint="curve")
            radius = width // 2 + outline_width
            for x, y in points:
                draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=outline)
        draw.line(points, fill=fill, width=width, joint="curve")
        radius = width // 2
        for x, y in points:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)

    # Dark nautical tile, kept quiet so the telescope lens and Codex mark stay readable at 16 px.
    tile_mask = Image.new("L", (size, size), 0)
    tile_draw = ImageDraw.Draw(tile_mask)
    tile_draw.rounded_rectangle((64, 62, 960, 958), radius=220, fill=255)
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_mask = tile_mask.filter(ImageFilter.GaussianBlur(34))
    shifted_shadow_mask = Image.new("L", (size, size), 0)
    shifted_shadow_mask.paste(shadow_mask, (0, 18))
    shadow_fill = Image.new("RGBA", (size, size), (0, 0, 0, 130))
    shadow_fill.putalpha(shifted_shadow_mask.point(lambda alpha: min(alpha, 130)))
    shadow.alpha_composite(shadow_fill)
    icon.alpha_composite(shadow)
    add_mask(tile_mask, (7, 24, 48), (9, 47, 73))
    draw = ImageDraw.Draw(icon)
    draw.rounded_rectangle((64, 62, 960, 958), radius=220, outline=(116, 192, 221, 55), width=10)
    draw.ellipse((-180, 580, 720, 1260), fill=(19, 108, 154, 48))
    draw.ellipse((460, -180, 1220, 610), fill=(19, 153, 130, 34))
    for star_x, star_y, star_a in [(202, 196, 140), (858, 256, 115), (780, 788, 95), (160, 690, 90)]:
        draw.ellipse((star_x - 4, star_y - 4, star_x + 4, star_y + 4), fill=(230, 250, 255, star_a))

    brass_dark = (84, 54, 28, 255)
    brass_mid = (208, 139, 58, 255)
    brass_light = (255, 210, 116, 255)

    telescope_shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rounded_line(telescope_shadow, [(190, 784), (395, 674), (654, 540)], 214, (0, 0, 0, 120))
    icon.alpha_composite(telescope_shadow.filter(ImageFilter.GaussianBlur(20)))

    tube = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rounded_line(tube, [(176, 770), (382, 660), (660, 516)], 182, brass_mid, outline=brass_dark, outline_width=24)
    rounded_line(tube, [(174, 730), (386, 618), (634, 490)], 52, (255, 210, 116, 230), outline=None)
    rounded_line(tube, [(194, 830), (392, 724), (652, 590)], 42, (124, 73, 35, 170), outline=None)
    icon.alpha_composite(tube)

    band = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rounded_line(band, [(258, 734), (350, 686)], 222, (66, 43, 25, 255))
    rounded_line(band, [(264, 728), (356, 680)], 166, (244, 185, 82, 255))
    rounded_line(band, [(500, 608), (592, 560)], 226, (66, 43, 25, 255))
    rounded_line(band, [(506, 602), (598, 554)], 170, (239, 169, 70, 255))
    icon.alpha_composite(band)

    eyepiece = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rounded_line(eyepiece, [(98, 812), (230, 742)], 150, (53, 37, 26, 255), outline=(16, 23, 31, 210), outline_width=12)
    rounded_line(eyepiece, [(106, 800), (238, 730)], 104, (218, 151, 68, 255), outline=None)
    icon.alpha_composite(eyepiece)

    lens_shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(lens_shadow).ellipse((246, 132, 890, 776), fill=(0, 0, 0, 135))
    icon.alpha_composite(lens_shadow.filter(ImageFilter.GaussianBlur(24)))

    lens_cx, lens_cy = 568, 436
    outer_r, glass_r = 334, 258
    draw = ImageDraw.Draw(icon)
    draw.ellipse(
        (lens_cx - outer_r, lens_cy - outer_r, lens_cx + outer_r, lens_cy + outer_r),
        fill=brass_dark,
    )
    draw.ellipse(
        (lens_cx - outer_r + 30, lens_cy - outer_r + 30, lens_cx + outer_r - 30, lens_cy + outer_r - 30),
        fill=brass_mid,
    )
    draw.arc(
        (lens_cx - outer_r + 34, lens_cy - outer_r + 34, lens_cx + outer_r - 34, lens_cy + outer_r - 34),
        start=196,
        end=330,
        fill=brass_light,
        width=22,
    )
    draw.arc(
        (lens_cx - outer_r + 18, lens_cy - outer_r + 18, lens_cx + outer_r - 18, lens_cy + outer_r - 18),
        start=28,
        end=145,
        fill=(70, 44, 25, 165),
        width=28,
    )

    glass_mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(glass_mask).ellipse((lens_cx - glass_r, lens_cy - glass_r, lens_cx + glass_r, lens_cy + glass_r), fill=255)
    add_mask(glass_mask, (63, 214, 238), (37, 89, 255))
    draw = ImageDraw.Draw(icon)
    draw.ellipse(
        (lens_cx - glass_r, lens_cy - glass_r, lens_cx + glass_r, lens_cy + glass_r),
        outline=(211, 247, 255, 180),
        width=12,
    )
    draw.arc(
        (lens_cx - glass_r + 42, lens_cy - glass_r + 42, lens_cx + glass_r - 42, lens_cy + glass_r - 42),
        start=205,
        end=318,
        fill=(255, 255, 255, 105),
        width=18,
    )
    draw.ellipse((lens_cx - 180, lens_cy - 198, lens_cx - 72, lens_cy - 92), fill=(255, 255, 255, 80))

    mark_size = 350
    if CODEX_MARK_PATH.exists():
        mark = Image.open(CODEX_MARK_PATH).convert("RGBA").resize((mark_size, mark_size), Image.Resampling.LANCZOS)
    else:
        mark = Image.new("RGBA", (mark_size, mark_size), (0, 0, 0, 0))
        md = ImageDraw.Draw(mark)
        md.rounded_rectangle((24, 24, mark_size - 24, mark_size - 24), radius=78, fill=(250, 252, 255, 255))
        md.ellipse((72, 70, mark_size - 72, mark_size - 72), fill=(87, 104, 255, 255))
        font = load_font(104, bold=True)
        md.text((mark_size // 2, mark_size // 2 + 8), ">_", font=font, fill=(255, 255, 255, 255), anchor="mm")
    mark_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mark_layer.alpha_composite(mark, (lens_cx - mark_size // 2, lens_cy - mark_size // 2 + 6))
    mark_alpha = Image.new("L", (size, size), 0)
    mark_alpha.paste(mark.getchannel("A"), (lens_cx - mark_size // 2, lens_cy - mark_size // 2 + 6))
    visible_mark_alpha = Image.composite(mark_alpha, Image.new("L", (size, size), 0), glass_mask)
    mark_layer.putalpha(visible_mark_alpha)
    icon.alpha_composite(mark_layer)

    draw = ImageDraw.Draw(icon)
    draw.arc(
        (lens_cx - glass_r + 28, lens_cy - glass_r + 28, lens_cx + glass_r - 28, lens_cy + glass_r - 28),
        start=20,
        end=136,
        fill=(255, 255, 255, 115),
        width=20,
    )
    draw.ellipse((lens_cx + 114, lens_cy - 184, lens_cx + 166, lens_cy - 132), fill=(255, 255, 255, 125))
    draw.line((742, 728, 840, 818), fill=(238, 199, 102, 135), width=12)
    draw.line((772, 694, 884, 700), fill=(255, 240, 162, 105), width=9)

    icon = icon.resize((256, 256), Image.Resampling.LANCZOS)
    icon.save(path, format="ICO", sizes=sizes)
    return path


def set_window_icon(root: tk.Tk) -> None:
    with contextlib.suppress(Exception):
        if ICON_PATH.exists():
            root.iconbitmap(str(ICON_PATH))


def run_app() -> int:
    if tk is None:
        print(tr("tk_missing"))
        return 2
    if Image is None or ImageTk is None:
        print(tr("pillow_missing"))
        return 2
    set_dpi_awareness()
    config = load_config()
    try:
        with contextlib.suppress(Exception):
            if not ICON_PATH.exists():
                create_icon(ICON_PATH)
        root = tk.Tk()
        set_window_icon(root)
        UsageWidget(root, config)
        root.mainloop()
        return 0
    except Exception:
        log_line("UI crashed:\n" + traceback.format_exc())
        if messagebox:
            with contextlib.suppress(Exception):
                messagebox.showerror(tr("app_name"), tr("ui_crashed", path=LOG_PATH))
        return 1


def write_session_event(codex_home: pathlib.Path, payload: dict[str, Any], timestamp: str = "2026-06-25T09:56:30.302Z") -> pathlib.Path:
    session_dir = codex_home / "sessions" / "2026" / "06" / "25"
    session_dir.mkdir(parents=True, exist_ok=True)
    path = session_dir / "rollout-test.jsonl"
    event = {
        "timestamp": timestamp,
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "rate_limits": payload,
        },
    }
    path.write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_logs_rate_limit_event(codex_home: pathlib.Path, payload: dict[str, Any], timestamp: int | None = None) -> pathlib.Path:
    codex_home.mkdir(parents=True, exist_ok=True)
    path = codex_home / "logs_2.sqlite"
    con = sqlite3.connect(path)
    try:
        con.execute(
            """
            create table logs (
                id integer primary key autoincrement,
                ts integer not null,
                ts_nanos integer not null,
                level text not null,
                target text not null,
                feedback_log_body text,
                module_path text,
                file text,
                line integer,
                thread_id text,
                process_uuid text,
                estimated_bytes integer not null default 0
            )
            """
        )
        event = {
            "type": "codex.rate_limits",
            "plan_type": payload.get("plan_type", "plus"),
            "rate_limits": {
                "allowed": True,
                "limit_reached": False,
                "primary": payload["primary"],
                "secondary": payload["secondary"],
            },
            "credits": None,
        }
        body = "stream_request: websocket event: " + json.dumps(event, ensure_ascii=False)
        con.execute(
            """
            insert into logs (ts, ts_nanos, level, target, feedback_log_body)
            values (?, ?, ?, ?, ?)
            """,
            (timestamp or int(now_ts()), 0, "TRACE", "codex_api::endpoint::responses_websocket", body),
        )
        con.commit()
    finally:
        con.close()
    return path


def example_rate_limits(reset_offset: int = 3600) -> dict[str, Any]:
    reset = int(now_ts()) + reset_offset
    return {
        "limit_id": "codex",
        "limit_name": None,
        "primary": {
            "used_percent": 46.0,
            "window_minutes": FIVE_HOUR_MINUTES,
            "resets_at": reset,
        },
        "secondary": {
            "used_percent": 16.0,
            "window_minutes": WEEKLY_MINUTES,
            "resets_at": reset + 6 * 24 * 3600,
        },
        "credits": None,
        "individual_limit": None,
        "plan_type": "plus",
        "rate_limit_reached_type": None,
    }


class ReaderTests(unittest.TestCase):
    def test_extracts_five_hour_and_weekly_remaining(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = pathlib.Path(td) / ".codex"
            write_session_event(home, example_rate_limits())
            sample = CodexRateLimitReader({"codex_home": str(home)}).read()
            self.assertTrue(sample["ok"])
            self.assertEqual(sample["plan_type"], "plus")
            self.assertEqual(sample["windows"]["five_hour"]["remaining_percent"], 54.0)
            self.assertEqual(sample["windows"]["weekly"]["remaining_percent"], 84.0)
            self.assertFalse(sample["windows"]["five_hour"]["stale"])

    def test_reads_latest_rate_limit_from_large_session_tail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = pathlib.Path(td) / ".codex"
            path = write_session_event(home, example_rate_limits())
            event_line = path.read_text(encoding="utf-8")
            prefix = ('{"type":"noise","payload":"padding"}\n' * 30000)
            path.write_text(prefix + event_line, encoding="utf-8")
            sample = CodexRateLimitReader({"codex_home": str(home)}).read()
            self.assertTrue(sample["ok"])
            self.assertEqual(sample["windows"]["five_hour"]["remaining_percent"], 54.0)

    def test_extracts_rate_limits_from_logs_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = pathlib.Path(td) / ".codex"
            write_logs_rate_limit_event(home, example_rate_limits())
            sample = CodexRateLimitReader({"codex_home": str(home)}).read()
            self.assertTrue(sample["ok"])
            self.assertIn("logs_2.sqlite#logs:", str(sample["source_path"]))
            self.assertEqual(sample["windows"]["five_hour"]["remaining_percent"], 54.0)
            self.assertEqual(sample["windows"]["weekly"]["remaining_percent"], 84.0)

    def test_handles_limit_window_seconds_shape(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = pathlib.Path(td) / ".codex"
            reset = int(now_ts()) + 5000
            write_session_event(
                home,
                {
                    "rate_limit": {
                        "primary_window": {
                            "used_percent": 25,
                            "limit_window_seconds": FIVE_HOUR_MINUTES * 60,
                            "reset_at": reset,
                        },
                        "secondary_window": {
                            "used_percent": 5,
                            "limit_window_seconds": WEEKLY_MINUTES * 60,
                            "reset_at": reset + 10000,
                        },
                    },
                    "plan_type": "plus",
                },
            )
            sample = CodexRateLimitReader({"codex_home": str(home)}).read()
            self.assertEqual(sample["windows"]["five_hour"]["remaining_percent"], 75.0)
            self.assertEqual(sample["windows"]["weekly"]["remaining_percent"], 95.0)

    def test_does_not_treat_weekly_only_primary_as_five_hour(self) -> None:
        windows = normalize_rate_limits(
            {
                "primary": {
                    "used_percent": 1,
                    "window_minutes": WEEKLY_MINUTES,
                    "resets_at": int(now_ts()) + WEEKLY_MINUTES * 60,
                },
                "secondary": None,
            }
        )
        self.assertFalse(windows["five_hour"]["available"])
        self.assertTrue(windows["five_hour"]["not_offered"])
        self.assertTrue(windows["weekly"]["available"])
        self.assertEqual(windows["weekly"]["remaining_percent"], 99.0)

    def test_reads_plan_expiry_without_persisting_token(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = pathlib.Path(td) / ".codex"
            home.mkdir(parents=True)
            account = {
                "chatgpt_plan_type": "plus",
                "chatgpt_subscription_active_until": "2026-07-24T09:15:15+00:00",
                "chatgpt_subscription_last_checked": "2026-07-13T00:00:00+00:00",
            }
            payload = {"https://api.openai.com/auth": account}
            encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
            atomic_write_json(home / "auth.json", {"tokens": {"id_token": f"header.{encoded}.signature"}})
            metadata = read_local_plan_metadata(home)
            self.assertEqual(metadata["plan_type"], "plus")
            self.assertEqual(metadata["plan_expires_at"], parse_event_timestamp(account["chatgpt_subscription_active_until"]))
            self.assertNotIn("id_token", metadata)

    def test_counts_only_future_weekly_resets_before_plan_expiry(self) -> None:
        now = parse_event_timestamp("2026-07-14T08:47:34+08:00")
        next_reset = parse_event_timestamp("2026-07-21T09:12:05+08:00")
        plan_expires = parse_event_timestamp("2026-07-24T17:15:15+08:00")
        self.assertEqual(resets_before_expiry(next_reset, plan_expires, now=now), 1)
        self.assertEqual(resets_before_expiry(next_reset, next_reset - 1, now=now), 0)
        self.assertEqual(resets_before_expiry(next_reset, now - 1, now=now), 0)

    def test_uses_codex_credit_balance_for_resets_remaining(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = pathlib.Path(td) / ".codex"
            payload = example_rate_limits()
            payload["credits"] = {"has_credits": False, "unlimited": False, "balance": "0"}
            write_session_event(home, payload)
            sample = CodexRateLimitReader({"codex_home": str(home)}).read()
            self.assertEqual(sample["resets_remaining"], 0)
            self.assertEqual(sample["resets_source"], "credits")

            payload["credits"] = {"has_credits": True, "unlimited": False, "balance": "2"}
            write_session_event(home, payload, timestamp=int(now_ts()) + 1)
            sample = CodexRateLimitReader({"codex_home": str(home)}).read()
            self.assertEqual(sample["resets_remaining"], 2)

    def test_marks_expired_window_stale_without_hiding_value(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = pathlib.Path(td) / ".codex"
            write_session_event(home, example_rate_limits(reset_offset=-30))
            sample = CodexRateLimitReader({"codex_home": str(home)}).read()
            self.assertTrue(sample["ok"])
            self.assertEqual(sample["windows"]["five_hour"]["remaining_percent"], 54.0)
            self.assertTrue(sample["windows"]["five_hour"]["stale"])

    def test_cache_fallback_when_live_read_has_no_data(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            temp = pathlib.Path(td)
            home = temp / ".codex"
            cached = empty_sample({"codex_home": str(home)})
            cached["ok"] = True
            cached["source_state"] = "live"
            cached["source_event_at"] = now_ts() - 60
            cached["windows"] = normalize_rate_limits(example_rate_limits())
            cache_path = temp / "cache.json"
            atomic_write_json(cache_path, cached)

            sample = read_snapshot({"codex_home": str(home)}, cache=True, cache_path=cache_path)
            self.assertTrue(sample["ok"])
            self.assertEqual(sample["source_state"], "cache")
            self.assertEqual(sample["windows"]["weekly"]["remaining_percent"], 84.0)

    def test_renderer_returns_nonblank_image(self) -> None:
        if Image is None:
            self.skipTest("Pillow unavailable")
        sample = empty_sample()
        sample["ok"] = True
        sample["source_state"] = "live"
        sample["source_event_at"] = now_ts()
        sample["plan_type"] = "plus"
        sample["windows"] = normalize_rate_limits(example_rate_limits())
        renderer = CardRenderer()
        self.assertIsNotNone(renderer.glass_panel)
        self.assertEqual(renderer.glass_panel.size, (CardRenderer.WIDTH * CardRenderer.SCALE, CardRenderer.HEIGHT * CardRenderer.SCALE))
        image = renderer.render(sample)
        self.assertEqual(image.size, (CardRenderer.WIDTH, CardRenderer.HEIGHT))
        self.assertEqual(image.getpixel((0, 0)), (1, 2, 3))
        self.assertNotEqual(image.getpixel((CardRenderer.WIDTH // 2, CardRenderer.HEIGHT // 2)), (1, 2, 3))
        pixels = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
        self.assertGreater(len(set(pixels)), 50)

        rgba = renderer.render_rgba(sample)
        self.assertEqual(rgba.mode, "RGBA")
        corner_crop = rgba.getchannel("A").crop((0, 0, 32, 32))
        corner_alpha = list(
            corner_crop.get_flattened_data() if hasattr(corner_crop, "get_flattened_data") else corner_crop.getdata()
        )
        self.assertIn(0, corner_alpha)
        self.assertTrue(any(0 < alpha < 255 for alpha in corner_alpha))

        native = renderer.render_native(sample)
        self.assertEqual(native.mode, "RGB")
        self.assertNotEqual(native.getpixel((0, 0)), (1, 2, 3))

    def test_renderer_supports_english_and_chinese(self) -> None:
        if Image is None:
            self.skipTest("Pillow unavailable")
        global CURRENT_LANGUAGE
        previous = CURRENT_LANGUAGE
        try:
            for language in ("en", "zh"):
                CURRENT_LANGUAGE = language
                sample = empty_sample()
                sample["ok"] = True
                sample["source_state"] = "live"
                sample["source_event_at"] = now_ts()
                sample["plan_type"] = "plus"
                sample["windows"] = normalize_rate_limits(example_rate_limits())
                image = CardRenderer().render(sample, hover=True)
                self.assertEqual(image.size, (CardRenderer.WIDTH, CardRenderer.HEIGHT))
                self.assertIn(tr("status_live"), TRANSLATIONS[language].values())
        finally:
            CURRENT_LANGUAGE = previous


def run_tests(include_ui: bool = False) -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReaderTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if include_ui:
        if tk is None or ImageTk is None:
            print("UI smoke skipped: tkinter or Pillow unavailable")
            return 1

        def fake_snapshot(_config: dict[str, Any]) -> dict[str, Any]:
            sample = empty_sample()
            sample["ok"] = True
            sample["source_state"] = "live"
            sample["source_event_at"] = now_ts()
            sample["plan_type"] = "plus"
            sample["windows"] = normalize_rate_limits(example_rate_limits())
            sample["note"] = "UI smoke"
            return sample

        set_dpi_awareness()
        root = tk.Tk()
        set_window_icon(root)
        widget = UsageWidget(root, dict(DEFAULT_CONFIG), snapshot_func=fake_snapshot)
        root.after(180, lambda: widget.label.event_generate("<Enter>"))
        root.after(360, lambda: widget.label.event_generate("<Leave>"))
        root.after(650, widget.quit)
        root.mainloop()
        print("UI smoke ok")
    return 0 if result.wasSuccessful() else 1


def print_snapshot() -> int:
    print(json.dumps(read_snapshot(load_config(), cache=False), ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=tr("app_name"))
    parser.add_argument("--test", action="store_true", help=tr("arg_test"))
    parser.add_argument("--include-ui", action="store_true", help=tr("arg_include_ui"))
    parser.add_argument("--snapshot", action="store_true", help=tr("arg_snapshot"))
    parser.add_argument("--make-icon", action="store_true", help=tr("arg_make_icon"))
    args = parser.parse_args(argv)
    if args.test:
        return run_tests(include_ui=args.include_ui)
    if args.snapshot:
        return print_snapshot()
    if args.make_icon:
        print(create_icon())
        return 0
    return run_app()


if __name__ == "__main__":
    sys.exit(main())
