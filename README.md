# Duga

**Duga 1.1.1 'Berkut-AM' — Fully local personal daily briefing agent.**

Duga gathers fresh information from *your* keywords, websites, and social handles, summarizes it with an LLM (DeepSeek by default), and delivers a concise daily briefing to Telegram. Everything runs on your machine. Your targets, prompts, keys, history, and briefings stay private — the project author never sees them.

| | |
|---|---|
| **Version** | `1.1.1` |
| **Codename** | `Berkut-AM` |
| **Python** | 3.10+ |
| **License** | MIT |
| **Repo** | https://github.com/f-ritz/duga |

---

## What Duga does

At a high level, every run does this:

1. **Load config** — `targets.json` (what to watch) + `prompt.txt` (how to write) + `.env` (API keys).
2. **Gather live data**
   - Keyword web search (DuckDuckGo, free, no key).
   - Full-page website scrapes (main content via trafilatura, with BeautifulSoup fallback).
   - Social profiles:
     - **X / Twitter** — direct profile page fetch + web-search fallback for recent posts.
     - **Instagram** — direct profile URL scan (“whole profile at once”) + site-restricted search fallback. Private accounts yield whatever is publicly crawlable.
     - **LinkedIn / Facebook / Threads** — site-restricted web search by handle.
3. **Optional vision** — if media URLs were collected, briefly describe up to N images with a vision-capable model (DeepSeek or a `VISION_*` override).
4. **Chunk (default)** — if you track more than ~10 entries total (keywords + websites + social handles), Duga splits them into chunks, generates a mini-briefing per chunk, then synthesizes one final daily briefing. Keeps LLM quality high on large target lists.
5. **Continuity** — loads the last 14 days of saved briefings so the model can note follow-ups and changes (not copy them).
6. **Deliver** — saves `briefings/YYYY-MM-DD.md` locally and sends the briefing via your Telegram bot (long messages are split automatically).

The CLI skips the run if today’s briefing already exists (use `--force` to override). The Windows GUI always forces a fresh run when you click **Run Briefing Now**.

---

## Features (1.1.1 'Berkut-AM')

### Core pipeline
- Config-driven via simple files: `targets.json` + `prompt.txt` + `.env`
- Live web search, website scraping, and public social profile scanning
- Default model: **DeepSeek-V4-Flash** (`deepseek-v4-flash`) via OpenAI-compatible API
- 10-entry chunking + final synthesis (adjustable; set `0` for a single large LLM call)
- 14-day briefing history for continuity
- Local briefing archive under `briefings/`
- Daily logs under `logs/`
- Telegram delivery with Markdown and multi-part message splitting
- Optional image/vision analysis (`MAX_IMAGES_TO_ANALYZE`, default 5)
- Safe “already ran today” guard on CLI (overridable with `--force`)

### Targets you can track
| Kind | How you enter it | How it’s gathered |
|------|------------------|-------------------|
| **Keywords** | Free text | DuckDuckGo web search (OR-joined, up to 10 keywords in the query) |
| **Websites** | Full `https://…` URLs | Direct fetch + main-content extraction |
| **X / Twitter** | Handle only (no URL) | Profile page + search fallback |
| **Instagram** | Handle only | Profile page URL scan + search fallback |
| **LinkedIn / Facebook / Threads** | Handle / name | Site-restricted web search |
| **other** (in JSON) | Free-form | Generic web search |

### Windows desktop GUI
- Native **tkinter + ttk** UI (Segoe UI, notebook tabs)
- Tabs: **Prompt**, **Targets**, **API Keys & Telegram**, **Run & Schedule**
- Minimize to **system tray** on close (X); tray menu: Show / Run Briefing Now / Exit
- `--minimized` / `--tray` startup for login autostart
- Adjustable **auto-run time** (HH:MM GMT/UTC) + Auto-run checkbox
- Adjustable **chunk size** and **IG posts/profile** (stored in `settings.json`)
- Right-click Cut / Copy / Paste / Select All on Prompt (and JSON editor)
- Targets: list editors **and** advanced raw `targets.json` editor with Reload / Validate & Save / overwrite confirm
- **Multiple named instances** (own prompt + targets; shared API keys)
  - New Instance / Delete Instance / dropdown switcher
  - Folders under `instances/<name>/`
  - Auto-run queues **Main + all instances** and runs them **sequentially**
- Proper Inno Setup installer with silent in-place upgrades
- App icon for window, taskbar, EXE, and tray

### CLI
- `duga` / `duga init` / `duga --dry-run` / `duga --force` / `duga --schedule`
- `--config-dir`, `--targets`, `--prompt`, `--chunk-size`
- Config dir overrides via env: `DUGA_CONFIG_DIR` (also accepts legacy `RADAR_CONFIG_DIR`)

### Mobile (Android companion)
- Kivy GUI: Prompt, Targets, Keys & Telegram, Run
- One-tap **Run Briefing Now** using the same core pipeline when packaged with the APK
- Best as a config + manual-run companion; reliable daily scheduling is easier on desktop

### Privacy & data locality
- Zero telemetry / no phone-home
- Only network calls are ones you configure (LLM, Telegram, and public web fetches for your targets)
- Automatic one-time migration of old **Radar** user data into the Duga config dir when present

---

## Quick start (CLI)

### 1. Install

```bash
# pipx (isolated, recommended)
pipx install git+https://github.com/f-ritz/duga.git

# or pip (prefer a venv)
pip install git+https://github.com/f-ritz/duga.git
```

From source:

```bash
git clone https://github.com/f-ritz/duga.git
cd duga
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# Unix:    source .venv/bin/activate
pip install -e .
```

### 2. Bootstrap config

```bash
duga init
```

Creates your personal config directory:

| Platform | Default path |
|----------|----------------|
| Windows | `%APPDATA%\duga` |
| macOS | `~/Library/Application Support/duga` |
| Linux | `~/.config/duga` |

Contents after init:

- `targets.json` — keywords, social handles, websites
- `prompt.txt` — style / tone / length instructions for the LLM
- `.env.example` — copy to `.env` and fill in keys

Resolution order for the config directory:

1. `--config-dir` or env `DUGA_CONFIG_DIR` / `RADAR_CONFIG_DIR` / `DUGA_HOME` / `RADAR_HOME`
2. Current working directory if it looks like a Duga project (has `targets.json`)
3. Platform user config dir (table above)

If an old **Radar** config dir exists, Duga best-effort copies `targets.json`, `prompt.txt`, `.env`, and any `briefings/` / `logs/` into the new Duga location (without overwriting existing files).

### 3. Add API keys

```bash
cd %APPDATA%\duga   # or your config path from `duga init`
copy .env.example .env   # Windows
# cp .env.example .env   # Unix
```

Minimum `.env`:

```env
DEEPSEEK_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=987654321
```

Optional / advanced (see [Environment variables](#environment-variables)):

```env
DEEPSEEK_MODEL=deepseek-v4-flash
DUGA_CHUNK_SIZE=10
MAX_SEARCH_RESULTS=15
MAX_WEBSITES=20
MAX_IMAGES_TO_ANALYZE=5
VISION_MODEL=
VISION_API_KEY=
VISION_BASE_URL=
# Stored by the GUI for convenience; not used by the gather pipeline in 1.1.1:
# APIFY_API_KEY=
# BRAVE_API_KEY=
# TAVILY_API_KEY=
```

### 4. Customize targets and style

**`targets.json` example shape:**

```json
{
  "keywords": ["xAI", "AI agents", "DeepSeek V4"],
  "social": {
    "x": ["xai", "elonmusk"],
    "instagram": [],
    "linkedin": [],
    "facebook": [],
    "threads": [],
    "other": []
  },
  "websites": [
    "https://x.ai",
    "https://blog.x.ai"
  ]
}
```

- Social values are **handles / usernames**, not full profile URLs.
- Websites should be full `https://…` URLs (missing scheme is auto-prefixed with `https://`).

**`prompt.txt`** controls tone, length, priorities, and format. A template ships with the package (concise intelligence briefer, ~650–900 words, cite sources, use history for continuity only).

### 5. Test, then run

```bash
duga --dry-run          # gather only; print sample; no LLM, no Telegram
duga                    # full run: gather → LLM → save → Telegram
duga --force            # re-run even if today's briefing already exists
```

---

## How it works (detail)

### Gathering

| Source | Engine | Notes |
|--------|--------|--------|
| Keywords | DuckDuckGo text search | Free; no API key. Up to `MAX_SEARCH_RESULTS` (default 15). |
| Websites | `requests` + trafilatura (+ BS4 fallback) | ~12k chars capped per page; polite delay between fetches. |
| X | Profile HTML + DDG `from:handle` / `site:x.com/handle` | X is JS-heavy; expect best-effort public snippets. Optional `twscrape` extra for better X later. |
| Instagram | Profile URL fetch + DDG site search | No Apify actor in 1.1.1. Private profiles → limited public data. |
| Other social | DDG with `site:` hints | LinkedIn, Facebook, Threads. |

Web search and scrapes send `Cache-Control: no-cache` so content is as fresh as possible.

### Chunking & synthesis

- Default chunk size: **10 entries** (`DUGA_CHUNK_SIZE` or `--chunk-size`).
- An “entry” = one keyword **or** one website **or** one social handle.
- If total entries ≤ chunk size (or chunk size is `0`), a **single** gather + LLM call is used.
- Otherwise:
  1. Split targets into chunks.
  2. Gather + (optional vision) + LLM mini-briefing per chunk (no history in chunk calls).
  3. Synthesize all chunk briefings **plus** 14-day history into one final briefing.

This keeps each model call small. DeepSeek-V4-Flash advertises a very large context window; in practice quality is better with smaller, focused prompts — hence the default.

### History

- Briefings saved as `briefings/YYYY-MM-DD.md` with a UTC generation header.
- Last **14 days** loaded; each prior briefing truncated for the prompt (~1200 chars each, ~6000 chars total budget).
- Prompt rules tell the model to use history only for continuity / change detection.

### Delivery

- Telegram Bot API `sendMessage` (no heavy SDK).
- Markdown parse mode; falls back to plain text if Markdown fails.
- Messages longer than ~4k chars are split into numbered parts.
- Failures still leave the local briefing on disk.

---

## Command line reference

```bash
duga                          # generate + send (chunking default 10)
duga --dry-run                # gather + print; no LLM / Telegram
duga --force                  # ignore “already exists for today”
duga --chunk-size 0           # one big LLM call (no chunking)
duga --chunk-size 8           # custom chunk size
duga --config-dir PATH        # use another profile / instance folder
duga --targets PATH           # override targets.json path
duga --prompt PATH            # override prompt.txt path
duga --schedule               # long-running process; run at 12:00 UTC daily (needs apscheduler)
duga init                     # bootstrap config dir
duga init --path DIR          # bootstrap at a custom path
duga init --force             # overwrite existing template files
```

`--ig-post-limit` is accepted for compatibility but Instagram gathering no longer uses a per-handle post scrape limit (profiles are scanned via URL + search).

For multi-instance folders created by the GUI, point CLI at them:

```bash
duga --config-dir "%APPDATA%\duga\instances\Work"
```

Sub-instances inherit API keys from the parent `.env` when they do not have their own.

---

## Telegram setup

1. In Telegram, open **@BotFather** → `/newbot` → copy the **bot token** into `TELEGRAM_BOT_TOKEN`.
2. Message your new bot at least once (e.g. “hi”) so it can reply to you.
3. Open **@userinfobot** or **@getmyid_bot** → copy your numeric **Chat ID** into `TELEGRAM_CHAT_ID`.

The bot can only message chats that have started a conversation with it (or where it is a member, for groups).

---

## Environment variables

| Variable | Required | Default / notes |
|----------|----------|-----------------|
| `DEEPSEEK_API_KEY` | **Yes** | LLM key (OpenAI-compatible DeepSeek endpoint) |
| `TELEGRAM_BOT_TOKEN` | **Yes** (to deliver) | From @BotFather |
| `TELEGRAM_CHAT_ID` | **Yes** (to deliver) | Your user/chat id |
| `DEEPSEEK_MODEL` | No | `deepseek-v4-flash` |
| `DUGA_CHUNK_SIZE` | No | `10` (`0` = disable chunking) |
| `DUGA_IG_POST_LIMIT` | No | Stored for compatibility; IG uses profile scan, not a post-limit scraper |
| `MAX_SEARCH_RESULTS` | No | `15` |
| `MAX_WEBSITES` | No | `20` |
| `MAX_IMAGES_TO_ANALYZE` | No | `5` |
| `VISION_MODEL` / `VISION_API_KEY` / `VISION_BASE_URL` | No | Optional vision overrides; falls back to main DeepSeek client/model |
| `DUGA_CONFIG_DIR` | No | Override config directory |
| `RADAR_CONFIG_DIR` | No | Legacy alias for `DUGA_CONFIG_DIR` |
| `APIFY_API_KEY` | No | Accepted in GUI; **not used for Instagram** in 1.1.1 |
| `BRAVE_API_KEY` / `TAVILY_API_KEY` | No | Accepted in GUI; **gather currently uses DuckDuckGo only** |

---

## Scheduling daily runs

Time is always treated as **GMT / UTC**.

### Windows GUI (recommended on desktop)

1. Set **Time (GMT)** (e.g. `12:00` or `09:30`) → **Set**.
2. Enable **Auto-run daily at configured time GMT**.
3. Keep the app running (OK minimized to tray). Installer can add a Startup entry with `--minimized`.
4. At the configured time, **Main + every instance under `instances/`** run **one after another**.

Settings persist in `settings.json` in the main data dir (`run_time`, `chunk_size`, `ig_posts_limit`).

### Windows Task Scheduler (CLI)

```powershell
schtasks /create /sc daily /st 12:00 /tn "DugaBriefing" /tr "duga" /ru %USERNAME%
```

Adjust `/st` for your preferred local wall-clock time if you prefer Task Scheduler’s local time; the GUI path is UTC.

### macOS / Linux (cron)

```cron
0 12 * * * /path/to/duga >> /path/to/duga-logs/cron.log 2>&1
```

### Long-running CLI scheduler

```bash
pip install apscheduler   # or: pip install -e ".[schedule]"
duga --schedule           # fixed 12:00 UTC in 1.1.1 CLI; use GUI for custom HH:MM
```

---

## Windows Desktop GUI + installer

See **[`windows/README.md`](windows/README.md)** for build and installer details.

Short version:

```powershell
python windows\duga_gui.py
python windows\duga_gui.py --minimized

# Build onedir dist for packaging
python windows\build_exe.py
# Then compile windows\DugaInstaller.iss with Inno Setup
# → dist\DugaSetup-1.1.1-Berkut-AM.exe
```

Installer installs to `%LocalAppData%\Duga`, Start Menu shortcuts, Startup (minimized tray), proper uninstaller, and **silent upgrade** when you run a newer setup over an old install.

User data (keys, targets, prompts, briefings, instances) lives in the **config/data directory**, not inside the install folder, so it survives app updates.

### GUI layout (quick map)

| Area | What it does |
|------|----------------|
| Top bar | Title, **Run Briefing Now** |
| Status bar | Config path, Auto-run checkbox, Time (GMT), Chunk size, IG posts/profile |
| Instance bar | Dropdown, New Instance, Delete Instance |
| **Prompt** tab | Style instructions → `prompt.txt` |
| **Targets** tab | Keywords, websites, X/IG/LinkedIn/Facebook/Threads lists + advanced JSON editor |
| **API Keys & Telegram** | Local `.env` fields |
| **Run & Schedule** | Run button + live activity log |
| Tray | Show, Run Briefing Now, Exit |

---

## Android app

See **[`mobile/README.md`](mobile/README.md)**.

```bash
pip install kivy
python mobile/duga_kivy_app.py

# APK (Linux / WSL recommended)
cd mobile
buildozer android debug
```

Limitations on Android: OS battery/Doze restrictions make exact daily background runs unreliable; social scrapes can be flaky without login cookies. Many users edit config on the phone and keep scheduled runs on a desktop/server.

---

## Project layout

```
duga/
├── README.md                 # this file
├── pyproject.toml            # package metadata, version 1.1.1, console script `duga`
├── requirements.txt
├── LICENSE
├── icon.ico / radar.ico      # app icons
├── src/duga/
│   ├── __init__.py           # __version__, DISPLAY_VERSION
│   ├── main.py               # CLI entry, run_once, scheduler
│   ├── config.py             # paths, targets/prompt/env loaders, migration
│   ├── gather.py             # search, scrape, social, chunk helpers
│   ├── llm.py                # DeepSeek generate + synthesize + vision
│   ├── history.py            # save/load last 14 days
│   ├── telegram_bot.py       # Bot API sender
│   └── templates/            # default targets.json + prompt.txt
├── windows/
│   ├── duga_gui.py           # desktop GUI + tray + multi-instance
│   ├── build_exe.py          # PyInstaller onedir
│   ├── DugaInstaller.iss     # Inno Setup
│   └── README.md
└── mobile/
    ├── duga_kivy_app.py
    ├── buildozer.spec
    └── README.md
```

---

## Development

```bash
pip install -e ".[full]"      # includes apscheduler + twscrape optional extras
duga init
duga --dry-run
```

Optional extras from `pyproject.toml`:

| Extra | Packages |
|-------|----------|
| `schedule` | `apscheduler` |
| `full` | `apscheduler`, `twscrape` |
| `mobile` | `kivy`, `kivymd` |
| `windows` | (none — uses stdlib tkinter; tray needs `pywin32` at build/dev time) |

---

## Privacy

**Zero telemetry. Zero phoning home.**

- No accounts with this project.
- No data is sent to the author or any central Duga server.
- External calls are only what you configure or enable by listing targets:
  - DeepSeek (or another model you point the OpenAI-compatible client at)
  - Your Telegram bot
  - Public web/search fetches for keywords, sites, and handles you chose
- Config, history, and briefings live only on your disk.

You can audit the code, fork it, or run mostly air-gapped aside from the LLM + delivery + fetch steps.

---

## Version history (high level)

| Version | Codename | Highlights |
|---------|----------|------------|
| **1.1.1** | **Berkut-AM** | Multi-instance GUI, adjustable GMT auto-run, chunk controls, advanced JSON targets editor, prompt context menu, Instagram via direct profile scan (no Apify for IG), tray + installer polish |
| 1.1.0 | Berkut-AM | Multi-instance + auto-run queue foundations |
| 1.0.x | Berkut-M | First full desktop product release line |
| 0.2.x / 0.1.x | Berkut… | Early GUI, rebrand from Radar → Duga |

Installer artifacts are named like `DugaSetup-1.1.1-Berkut-AM.exe`.

---

## Getting API keys

| Service | URL | Role in 1.1.1 |
|---------|-----|----------------|
| DeepSeek | https://platform.deepseek.com | **Required** LLM (`deepseek-v4-flash` recommended) |
| Telegram | @BotFather + chat-id bots | **Required** delivery |
| DuckDuckGo | (none) | Default free web search |
| Vision override | Any OpenAI-style vision endpoint | Optional image descriptions |
| Apify / Brave / Tavily | respective sites | Fields exist in GUI; **not wired into gather** in this version |

---

**Duga 1.1.1 'Berkut-AM'** — install, configure once, run from tray or scheduler. Fresh content every time. Multiple named instances supported. Your data survives updates.
