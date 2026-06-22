"""Configuration loading for radar.

targets.json and prompt.txt are the primary user-editable inputs.
They are intentionally simple and human-editable so they can be expanded at will.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Project root = directory containing this file
ROOT = Path(__file__).resolve().parent
BRIEFINGS_DIR = ROOT / "briefings"
LOGS_DIR = ROOT / "logs"

DEFAULT_TARGETS = ROOT / "targets.json"
DEFAULT_PROMPT = ROOT / "prompt.txt"


@dataclass
class Targets:
    keywords: list[str] = field(default_factory=list)
    social: dict[str, list[str]] = field(default_factory=dict)
    websites: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Targets":
        return cls(
            keywords=list(data.get("keywords", [])),
            social={k: list(v) for k, v in data.get("social", {}).items()},
            websites=list(data.get("websites", [])),
        )


def load_targets(path: Path | str | None = None) -> Targets:
    """Load and validate targets.json. Creates a minimal example if missing."""
    p = Path(path) if path else DEFAULT_TARGETS
    if not p.exists():
        example = {
            "keywords": ["xAI", "Grok"],
            "social": {"x": ["xai"]},
            "websites": ["https://x.ai"],
        }
        p.write_text(json.dumps(example, indent=2), encoding="utf-8")
        print(f"[config] Created example targets at {p}")
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    return Targets.from_dict(data)


def load_prompt(path: Path | str | None = None) -> str:
    """Load the raw user style prompt (prompt.txt)."""
    p = Path(path) if path else DEFAULT_PROMPT
    if not p.exists():
        default = (
            "You are a concise, neutral daily briefing writer.\n"
            "Focus on high-signal developments only.\n"
        )
        p.write_text(default, encoding="utf-8")
        print(f"[config] Created example prompt at {p}")
    return p.read_text(encoding="utf-8").strip()


def load_env() -> None:
    """Load .env if present. Safe to call multiple times."""
    load_dotenv(ROOT / ".env")


def get_env(key: str, default: str | None = None) -> str | None:
    val = os.getenv(key, default)
    if val is None:
        return None
    return val.strip()


def ensure_dirs() -> None:
    BRIEFINGS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
