#!/usr/bin/env python3
"""radar — Daily AI briefing agent.

Run once per day (ideally triggered at 12:00 GMT via Task Scheduler).

Usage:
    python main.py                 # normal run (sends if everything is configured)
    python main.py --dry-run       # collect data + build prompt, skip LLM + send
    python main.py --force         # ignore "already sent today" guard
    python main.py --schedule      # (future) run scheduler loop

Environment and input files:
    See README.md and .env.example
"""
from __future__ import annotations

import argparse
import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from config import (
    DEFAULT_PROMPT,
    DEFAULT_TARGETS,
    LOGS_DIR,
    ensure_dirs,
    get_env,
    load_env,
    load_prompt,
    load_targets,
)
from gather import CollectedData, format_for_llm, gather_all
from history import (
    briefing_exists,
    format_recent_for_prompt,
    get_today_str,
    load_recent_briefings,
    save_briefing,
)
from llm import analyze_images, generate_briefing
from telegram_bot import send_long_message

# Logging setup
ensure_dirs()
LOG_FILE = LOGS_DIR / f"radar_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("radar")


def setup_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="radar daily briefing generator")
    p.add_argument("--dry-run", action="store_true", help="Collect data and show prompt, do not call LLM or send")
    p.add_argument("--force", action="store_true", help="Run even if a briefing for today already exists")
    p.add_argument("--targets", type=Path, default=DEFAULT_TARGETS, help="Path to targets.json")
    p.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT, help="Path to prompt.txt")
    p.add_argument("--schedule", action="store_true", help="Run in scheduler mode (loop until 12:00 UTC daily)")
    return p


def run_once(dry_run: bool = False, force: bool = False, targets_path: Path | None = None, prompt_path: Path | None = None) -> int:
    load_env()
    ensure_dirs()

    today = get_today_str()

    if briefing_exists(today) and not force:
        log.info("Briefing for %s already exists. Use --force to override.", today)
        return 0

    # 1. Load user inputs
    targets = load_targets(targets_path)
    user_style = load_prompt(prompt_path)
    log.info("Loaded targets: %d keywords, %d social platforms, %d websites",
             len(targets.keywords), len(targets.social), len(targets.websites))

    # 2. Gather intelligence
    data: CollectedData = gather_all(targets)
    collected_text = format_for_llm(data)

    # 3. Load recent history for continuity
    recent = load_recent_briefings()
    recent_text = format_recent_for_prompt(recent)
    log.info("Loaded %d previous briefings for context", len(recent))

    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN — collected intelligence (first 4000 chars)")
        print("=" * 60)
        print(collected_text[:4000])
        print("\n" + "=" * 60)
        print("STYLE PROMPT (from prompt.txt)")
        print("=" * 60)
        print(user_style[:1500])
        if recent_text:
            print("\n--- Recent briefings context included ---")
        print("\n[DRY RUN] No LLM call or Telegram message was made.")
        return 0

    # 4. (Optional) analyze a few images if any were collected
    image_analyses = []
    if data.media_urls:
        log.info("Running vision analysis on %d images...", len(data.media_urls))
        try:
            image_analyses = analyze_images(data.media_urls, context="Daily briefing media")
        except Exception as e:
            log.warning("Vision analysis failed (continuing without): %s", e)

    if image_analyses:
        # Append short image summaries to collected_text
        img_block = "\n\n## IMAGE ANALYSIS RESULTS\n"
        for ia in image_analyses:
            img_block += f"- {ia['url']}: {ia.get('description', '')[:400]}\n"
        collected_text += img_block

    # 5. Generate briefing via LLM
    log.info("Calling LLM (%s) ...", get_env("DEEPSEEK_MODEL") or "deepseek-v4-flash")
    try:
        briefing = generate_briefing(
            user_style_prompt=user_style,
            collected_text=collected_text,
            recent_briefings_text=recent_text,
        )
    except Exception as e:
        log.error("LLM generation failed: %s", e)
        log.debug(traceback.format_exc())
        # Still save a minimal error report
        error_brief = f"# Briefing generation failed on {today}\n\nError: {e}\n\nSee logs."
        save_briefing(today, error_brief)
        return 1

    if not briefing or len(briefing) < 40:
        log.error("LLM returned empty or tiny briefing. Aborting send.")
        save_briefing(today, "# Empty briefing generated\n\n" + (briefing or ""))
        return 1

    # 6. Send
    log.info("Sending via Telegram...")
    sent = send_long_message(briefing)

    # 7. Persist
    save_briefing(today, briefing)
    log.info("Briefing saved to briefings/%s.md", today)

    if sent:
        log.info("Telegram message sent successfully.")
    else:
        log.warning("Telegram send reported failure. Briefing is still saved locally.")

    return 0


def run_scheduler_loop():
    """Very simple scheduler: sleep until next 12:00 UTC, then run.

    Better to use Windows Task Scheduler for a home computer.
    This is provided as a convenience for people who want a single persistent process.
    """
    from time import sleep

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        log.error("apscheduler not installed. pip install apscheduler or use Task Scheduler instead.")
        return 1

    log.info("Starting scheduler mode — will trigger at 12:00 UTC daily.")

    def job():
        log.info("Scheduled run triggered")
        try:
            run_once(dry_run=False, force=False)
        except Exception as e:
            log.exception("Scheduled job failed: %s", e)

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(job, "cron", hour=12, minute=0)
    scheduler.start()

    try:
        # Keep process alive
        while True:
            sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
    return 0


def main() -> int:
    parser = setup_argparser()
    args = parser.parse_args()

    if args.schedule:
        return run_scheduler_loop()

    return run_once(
        dry_run=args.dry_run,
        force=args.force,
        targets_path=args.targets,
        prompt_path=args.prompt,
    )


if __name__ == "__main__":
    sys.exit(main())
