#!/usr/bin/env python3
"""Duga — Personal daily AI briefing agent.

Fully local. Your targets, prompts, history and briefings never leave your computer
except for the explicit API calls you configure (LLM + notification).

After `pip install`, the command is usually available as:

    duga --help
    duga init
    duga --dry-run
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from .config import (
    CONFIG_DIR,
    DEFAULT_PROMPT,
    DEFAULT_TARGETS,
    LOGS_DIR,
    ensure_dirs,
    get_data_dir_info,
    get_env,
    load_env,
    load_prompt,
    load_targets,
)
from .gather import format_for_llm, gather_all
from .history import (
    briefing_exists,
    format_recent_for_prompt,
    get_today_str,
    load_recent_briefings,
    save_briefing,
)
from .llm import analyze_images, generate_briefing
from .telegram_bot import send_long_message

log = logging.getLogger("duga")


def _setup_logging() -> None:
    """Configure logging once we know the config dir."""
    ensure_dirs()
    log_file = LOGS_DIR / f"duga_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def setup_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="duga",
        description="Personal daily briefing agent (runs locally on your machine)"
    )
    p.add_argument("--config-dir", type=Path, default=None,
                   help="Override the directory used for targets.json, .env, briefings, etc.")
    p.add_argument("--dry-run", action="store_true",
                   help="Gather data, build prompt, print what would be sent. No LLM call or delivery.")
    p.add_argument("--force", action="store_true",
                   help="Run even if a briefing for today already exists")
    p.add_argument("--targets", type=Path, default=None,
                   help="Override path to targets.json")
    p.add_argument("--prompt", type=Path, default=None,
                   help="Override path to prompt.txt")
    p.add_argument("--schedule", action="store_true",
                   help="Run continuously and trigger at 12:00 UTC daily (uses apscheduler)")

    sub = p.add_subparsers(dest="command")
    init_p = sub.add_parser("init", help="Bootstrap a new duga configuration directory")
    init_p.add_argument("--path", type=Path, default=None,
                        help="Where to create the config (default: platform user config dir)")
    init_p.add_argument("--force", action="store_true", help="Overwrite existing files")

    return p


def do_init(path: Path | None = None, overwrite: bool = False) -> int:
    """Create a ready-to-use configuration directory with examples."""
    target_dir = Path(path).resolve() if path else CONFIG_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    files_to_create = {
        "targets.json": "targets.json",
        "prompt.txt": "prompt.txt",
        ".env.example": ".env.example",   # we will also ship this
    }

    created = []
    for dest_name, template_name in files_to_create.items():
        dest = target_dir / dest_name
        if dest.exists() and not overwrite:
            print(f"[init] Skipping existing: {dest}")
            continue

        # Try to copy from package templates
        copied = False
        try:
            from importlib.resources import as_file, files
            pkg = files("duga")
            tmpl = pkg / "templates" / template_name
            if tmpl.is_file():
                with as_file(tmpl) as src:
                    shutil.copy2(src, dest)
                copied = True
        except Exception:
            pass

        if not copied:
            # Fallbacks
            candidates = [
                Path.cwd() / template_name,
                Path.cwd() / ".env.example" if "env" in template_name else None,
                Path(__file__).parent / "templates" / template_name,
            ]
            for cand in candidates:
                if cand and cand.exists():
                    shutil.copy2(cand, dest)
                    copied = True
                    break

        if copied:
            created.append(dest)
        else:
            # Minimal fallbacks
            if "targets" in dest_name:
                dest.write_text('{"keywords": ["example"], "social": {}, "websites": []}', encoding="utf-8")
            elif "prompt" in dest_name:
                dest.write_text("You are a concise daily briefer.\n", encoding="utf-8")
            elif "env" in dest_name:
                dest.write_text("# Copy to .env and fill in your keys\nDEEPSEEK_API_KEY=\nTELEGRAM_BOT_TOKEN=\n", encoding="utf-8")
            created.append(dest)

    # Always ensure .env.example is there
    env_ex = target_dir / ".env.example"
    if not env_ex.exists() or overwrite:
        env_ex.write_text(
            "# LLM API Key (e.g. DeepSeek)\nDEEPSEEK_API_KEY=sk-...\n\n"
            "# Telegram (required)\nTELEGRAM_BOT_TOKEN=...\nTELEGRAM_CHAT_ID=...\n",
            encoding="utf-8"
        )

    print(f"\n[init] Duga configuration directory ready at:\n  {target_dir}")
    print("\nNext steps:")
    print(f"  1. cd {target_dir}")
    print("  2. copy .env.example .env   (then edit with your keys)")
    print("  3. Edit targets.json and prompt.txt to your liking")
    print("  4. duga --dry-run")
    print("  5. Set up daily scheduling (see README)")
    return 0


def run_once(
    dry_run: bool = False,
    force: bool = False,
    targets_path: Path | None = None,
    prompt_path: Path | None = None,
    config_dir: Path | None = None,
) -> int:
    _setup_logging()
    load_env()

    if config_dir:
        targets_path = targets_path or (config_dir / "targets.json")
        prompt_path = prompt_path or (config_dir / "prompt.txt")
        ensure_dirs(config_dir)
        log.info("Using config dir: %s", config_dir)
    else:
        ensure_dirs()
        log.info("Using config dir: %s", CONFIG_DIR)

    today = get_today_str()

    if briefing_exists(today) and not force:
        log.info("Briefing for %s already exists. Use --force to override.", today)
        return 0

    targets = load_targets(targets_path)
    user_style = load_prompt(prompt_path)
    log.info("Loaded targets: %d keywords, %d social platforms, %d websites",
             len(targets.keywords), len(targets.social), len(targets.websites))

    data = gather_all(targets)
    collected_text = format_for_llm(data)

    recent = load_recent_briefings()
    recent_text = format_recent_for_prompt(recent)
    log.info("Loaded %d previous briefings for context", len(recent))

    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN — collected intelligence (first 4500 chars)")
        print("=" * 60)
        print(collected_text[:4500])
        print("\n" + "=" * 60)
        print("STYLE PROMPT")
        print("=" * 60)
        print(user_style[:2000])
        print("\n[DRY RUN] No LLM call and no message was sent.")
        return 0

    # Optional vision
    if data.media_urls:
        try:
            analyses = analyze_images(data.media_urls)
            if analyses:
                img_block = "\n\n## IMAGE ANALYSIS\n" + "\n".join(
                    f"- {a['url']}: {a.get('description','')[:300]}" for a in analyses
                )
                collected_text += img_block
        except Exception as e:
            log.warning("Vision step skipped: %s", e)

    log.info("Calling LLM...")
    try:
        briefing = generate_briefing(user_style, collected_text, recent_text)
    except Exception as e:
        log.error("LLM failed: %s", e)
        log.debug(traceback.format_exc())
        save_briefing(today, f"# Generation failed\n\n{e}")
        return 1

    if not briefing or len(briefing) < 30:
        log.error("LLM produced very little content.")
        save_briefing(today, briefing or "# Empty")
        return 1

    save_briefing(today, briefing)
    log.info("Briefing saved.")

    sent = send_long_message(briefing)
    if sent:
        log.info("Delivered via Telegram.")
    else:
        log.warning("Delivery may have failed (briefing saved locally).")

    return 0


def run_scheduler_loop():
    from time import sleep
    _setup_logging()

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        log.error("Install apscheduler for --schedule mode: pip install apscheduler")
        return 1

    log.info("Scheduler started. Will run at 12:00 UTC daily.")

    def job():
        try:
            run_once(dry_run=False, force=False)
        except Exception:
            log.exception("Scheduled job error")

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(job, "cron", hour=12, minute=0)
    scheduler.start()

    try:
        while True:
            sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
    return 0


def main(argv: list[str] | None = None) -> int:
    # Very early override: detect --config-dir before heavy imports pull CONFIG_DIR
    import os, sys
    effective_argv = argv if argv is not None else sys.argv[1:]
    cfg_dir = None
    for i, tok in enumerate(effective_argv):
        if tok in ("--config-dir", "-c") and i + 1 < len(effective_argv):
            p = Path(effective_argv[i + 1]).resolve()
            os.environ["DUGA_CONFIG_DIR"] = str(p)
            cfg_dir = p
            break

    # Now safe to do full arg parsing + imports
    parser = setup_argparser()
    args = parser.parse_args(argv)

    if args.config_dir:
        cfg_dir = args.config_dir.resolve()
        os.environ["DUGA_CONFIG_DIR"] = str(cfg_dir)

    # Force config module to re-evaluate with env var if we set it
    if cfg_dir:
        import importlib
        import duga.config as cfgmod
        importlib.reload(cfgmod)
        cfgmod.CONFIG_DIR = cfg_dir
        cfgmod.BRIEFINGS_DIR = cfg_dir / "briefings"
        cfgmod.LOGS_DIR = cfg_dir / "logs"
        cfgmod.DEFAULT_TARGETS = cfg_dir / "targets.json"
        cfgmod.DEFAULT_PROMPT = cfg_dir / "prompt.txt"

    if args.command == "init":
        return do_init(args.path, overwrite=getattr(args, "force", False))

    if args.schedule:
        return run_scheduler_loop()

    return run_once(
        dry_run=args.dry_run,
        force=args.force,
        targets_path=args.targets,
        prompt_path=args.prompt,
        config_dir=cfg_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
