"""Configuration and path handling for Duga.

This module is the heart of making the tool distributable:

- User data (configs, briefings, logs) lives in a **user data directory**.
- Priority for locating config:
  1. --config-dir / DUGA_CONFIG_DIR (or RADAR_CONFIG_DIR for compatibility) environment variable (explicit override)
  2. Current working directory, *if* it looks like a duga project (has targets.json)
  3. Platform-standard user config dir (via platformdirs):
       - Windows: %APPDATA%\\duga
       - macOS: ~/Library/Application Support/duga
       - Linux: ~/.config/duga

- Example config files (targets.json, prompt.txt) are shipped inside the
  package as templates and copied by `duga init`.

Everything stays 100% on the user's machine.
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    import platformdirs
except ImportError:
    platformdirs = None  # Will fall back gracefully

# ------------------------------------------------------------------
# Core resolution of the "duga home" (user data directory)
# ------------------------------------------------------------------

def _get_explicit_config_dir() -> Path | None:
    """Check RADAR_CONFIG_DIR env or similar."""
    for key in ("DUGA_CONFIG_DIR", "RADAR_CONFIG_DIR", "DUGA_HOME", "RADAR_HOME"):
        val = os.getenv(key)
        if val:
            return Path(val).expanduser().resolve()
    return None


def _looks_like_duga_project(path: Path) -> bool:
    """Heuristic: does this directory contain user duga config files?"""
    return (path / "targets.json").exists() or (path / ".duga").exists()


def get_config_dir() -> Path:
    """
    Return the directory that holds this user's targets.json, .env,
    briefings/, logs/, etc.

    Respects overrides for power users and developers.
    """
    explicit = _get_explicit_config_dir()
    if explicit:
        explicit.mkdir(parents=True, exist_ok=True)
        return explicit

    cwd = Path.cwd().resolve()
    if _looks_like_duga_project(cwd):
        return cwd

    if platformdirs is not None:
        # Standard per-user location
        user_dir = Path(platformdirs.user_config_dir("duga", appauthor=False))
    else:
        # Fallback if platformdirs not installed
        home = Path.home()
        if os.name == "nt":
            user_dir = home / "AppData" / "Roaming" / "duga"
        else:
            user_dir = home / ".config" / "duga"

    user_dir.mkdir(parents=True, exist_ok=True)

    # Migrate from old "radar" config dir if present (for version updates / rebrand)
    old_radar = None
    if platformdirs is not None:
        old_radar = Path(platformdirs.user_config_dir("radar", appauthor=False))
    else:
        home = Path.home()
        if os.name == "nt":
            old_radar = home / "AppData" / "Roaming" / "radar"
        else:
            old_radar = home / ".config" / "radar"
    if old_radar and old_radar.exists() and old_radar != user_dir:
        try:
            for f in ["targets.json", "prompt.txt", ".env"]:
                src = old_radar / f
                dst = user_dir / f
                if src.exists() and not dst.exists():
                    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            # briefings and logs too if desired
            for sub in ["briefings", "logs"]:
                old_sub = old_radar / sub
                if old_sub.exists():
                    new_sub = user_dir / sub
                    new_sub.mkdir(exist_ok=True)
                    for f in old_sub.iterdir():
                        if f.is_file() and not (new_sub / f.name).exists():
                            (new_sub / f.name).write_bytes(f.read_bytes())
        except Exception:
            pass  # best effort

    return user_dir


# Directories derived from config dir
CONFIG_DIR = get_config_dir()
BRIEFINGS_DIR = CONFIG_DIR / "briefings"
LOGS_DIR = CONFIG_DIR / "logs"

# Default file locations (can be overridden by passing paths to loaders)
DEFAULT_TARGETS = CONFIG_DIR / "targets.json"
DEFAULT_PROMPT = CONFIG_DIR / "prompt.txt"
DEFAULT_ENV = CONFIG_DIR / ".env"


# ------------------------------------------------------------------
# Dataclass + loading logic (mostly unchanged)
# ------------------------------------------------------------------

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


def _copy_package_template(name: str, dest: Path) -> None:
    """Copy a template file that is shipped inside the duga package."""
    try:
        pkg_files = files("duga")
        template = pkg_files / "templates" / name
        if template.is_file():
            with as_file(template) as src:
                shutil.copy2(src, dest)
            return
    except Exception:
        pass

    # Fallback: try to find in source tree (when running from git clone)
    possible = [
        Path(__file__).parent / "templates" / name,
        Path.cwd() / name,
        Path.cwd() / "src" / "duga" / "templates" / name,
    ]
    for src in possible:
        if src.exists():
            shutil.copy2(src, dest)
            return

    # Last resort: write a minimal version
    if name == "targets.json":
        dest.write_text(json.dumps({
            "keywords": ["xAI", "AI agents"],
            "social": {"x": ["xai"]},
            "websites": ["https://example.com"]
        }, indent=2), encoding="utf-8")
    elif name == "prompt.txt":
        dest.write_text(
            "You are a concise, neutral daily briefing writer.\n"
            "Focus on high-signal developments only.\n",
            encoding="utf-8"
        )


def load_targets(path: Path | str | None = None) -> Targets:
    """Load targets.json. If missing, copy a template."""
    p = Path(path) if path else DEFAULT_TARGETS
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        _copy_package_template("targets.json", p)
        print(f"[config] Created example targets.json at {p}")
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    return Targets.from_dict(data)


def load_prompt(path: Path | str | None = None) -> str:
    """Load the user style prompt. Creates template if missing."""
    p = Path(path) if path else DEFAULT_PROMPT
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        _copy_package_template("prompt.txt", p)
        print(f"[config] Created example prompt.txt at {p}")
    return p.read_text(encoding="utf-8").strip()


def load_env(env_path: Path | str | None = None) -> None:
    """Load .env from the config directory (or explicit path)."""
    p = Path(env_path) if env_path else DEFAULT_ENV
    if p.exists():
        load_dotenv(p)
    else:
        # Also try the old behaviour of loading from CWD for backwards compat
        load_dotenv()


def get_env(key: str, default: str | None = None) -> str | None:
    val = os.getenv(key, default)
    if val is None:
        return None
    return val.strip()


def ensure_dirs(config_dir: Path | None = None) -> None:
    base = config_dir or CONFIG_DIR
    (base / "briefings").mkdir(parents=True, exist_ok=True)
    (base / "logs").mkdir(parents=True, exist_ok=True)


def get_data_dir_info() -> dict[str, str]:
    """Helpful for diagnostics."""
    return {
        "config_dir": str(CONFIG_DIR),
        "briefings_dir": str(BRIEFINGS_DIR),
        "logs_dir": str(LOGS_DIR),
    }
