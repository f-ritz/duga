"""Minimal Telegram sender using the Bot API directly (no extra heavy deps).

Requires:
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID (user id or chat id where you want the DM)
"""
from __future__ import annotations

import requests

from config import get_env, load_env

TELEGRAM_API = "https://api.telegram.org"


def send_message(text: str, chat_id: str | int | None = None, parse_mode: str = "Markdown") -> bool:
    """Send a message. Returns True on success."""
    load_env()
    token = get_env("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

    if chat_id is None:
        cid = get_env("TELEGRAM_CHAT_ID")
        if not cid:
            raise RuntimeError("TELEGRAM_CHAT_ID not set")
        chat_id = cid

    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text[:4096],  # Telegram hard limit per message
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.ok:
            return True
        print(f"[telegram] send failed: {r.status_code} {r.text[:300]}")
        # Try without parse_mode as fallback (some markdown may be invalid)
        payload.pop("parse_mode", None)
        r2 = requests.post(url, json=payload, timeout=30)
        return r2.ok
    except Exception as e:
        print(f"[telegram] exception: {e}")
        return False


def send_long_message(text: str, chat_id: str | int | None = None) -> bool:
    """Split long briefings into multiple messages if needed."""
    if len(text) <= 4000:
        return send_message(text, chat_id)

    chunks = []
    current = []
    for line in text.splitlines(keepends=True):
        current.append(line)
        if sum(len(x) for x in current) > 3800:
            chunks.append("".join(current))
            current = []
    if current:
        chunks.append("".join(current))

    success = True
    for i, chunk in enumerate(chunks):
        prefix = f"**Part {i+1}/{len(chunks)}**\n\n" if len(chunks) > 1 else ""
        if not send_message(prefix + chunk, chat_id, parse_mode="Markdown"):
            success = False
    return success
