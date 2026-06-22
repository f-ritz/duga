"""History handling: save briefings and load the last 14 days for context."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import BRIEFINGS_DIR, ensure_dirs

HISTORY_DAYS = 14


def _date_str(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d")


def get_today_str() -> str:
    return _date_str()


def get_briefing_path(date_str: str) -> Path:
    ensure_dirs()
    return BRIEFINGS_DIR / f"{date_str}.md"


def briefing_exists(date_str: str | None = None) -> bool:
    if date_str is None:
        date_str = get_today_str()
    return get_briefing_path(date_str).exists()


def save_briefing(date_str: str, content: str, meta: dict | None = None) -> Path:
    """Save the final briefing. Appends a small header with generation time."""
    ensure_dirs()
    path = get_briefing_path(date_str)
    header = f"# Daily Briefing — {date_str}\n\n_Generated at {datetime.now(timezone.utc).isoformat()} UTC_\n\n"
    path.write_text(header + content.strip() + "\n", encoding="utf-8")
    return path


def load_recent_briefings(max_days: int = HISTORY_DAYS) -> list[tuple[str, str]]:
    """Return list of (date_str, content) for the most recent briefings (oldest first)."""
    ensure_dirs()
    today = datetime.now(timezone.utc).date()
    results: list[tuple[str, str]] = []

    for i in range(max_days, -1, -1):  # go backwards, then reverse at end
        d = today - timedelta(days=i)
        ds = d.isoformat()
        p = get_briefing_path(ds)
        if p.exists():
            try:
                text = p.read_text(encoding="utf-8")
                results.append((ds, text))
            except Exception:
                pass

    # Keep only up to max_days, already in chronological order
    return results[-max_days:]


def format_recent_for_prompt(recent: list[tuple[str, str]], max_chars: int = 6000) -> str:
    """Compact representation of previous briefings for inclusion in the LLM prompt."""
    if not recent:
        return ""

    blocks = []
    for ds, full in recent:
        # Take the first ~1200 chars of each previous briefing as "memory"
        snippet = full[:1200].strip()
        blocks.append(f"### {ds}\n{snippet}\n")

    joined = "\n".join(blocks)
    if len(joined) > max_chars:
        joined = joined[:max_chars] + "\n... (truncated)"
    return joined
