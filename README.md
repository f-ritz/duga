# Duga

**Duga 1.1.1 'Berkut-AM' — Fully local personal daily briefing agent.**

Duga gathers information based on *your* keywords, social handles, and websites, summarizes the results with an LLM (DeepSeek / any OpenAI-compatible by default), and sends you a concise briefing via Telegram.

- Everything runs **on your own computer**.
- Your `targets.json`, `prompt.txt`, briefings, and data stay **private** — the author of this project never sees anything.
- Designed to be easy for anyone to install and run for themselves.
- Proper Windows installer with easy in-place updates, system tray, and background auto-run.

## Quick Start (for normal users)

### 1. Install (CLI)

**Recommended (cleanest):**

```bash
# Using pipx (isolated, great)
pipx install git+https://github.com/yourname/duga.git

# Or with regular pip (in a venv is fine)
pip install git+https://github.com/yourname/duga.git
```

After install you get the `duga` command.

**Alternative (from source / developers):**

```bash
git clone https://github.com/yourname/duga.git
cd duga
python -m venv .venv
source .venv/bin/activate   # or .\.venv\Scripts\Activate.ps1 on Windows
pip install -e .
```

### 2. Bootstrap your personal configuration

```bash
duga init
```

This creates your personal config directory (usually `~/.config/duga` on Linux/macOS or `%APPDATA%\duga` on Windows) containing:

- `targets.json`
- `prompt.txt`
- `.env.example`

User data (keys, targets, prompts, briefings) lives in a persistent user directory and is preserved across version updates via automatic migration.

### 3. Add your API keys (see detailed setup below)

```bash
# Go to your config directory (duga init tells you the path)
cd "$(duga --help | grep -i config || echo "$HOME/.config/duga")"   # or manually
cp .env.example .env
```

Edit `.env` and fill in at minimum:

```env
DEEPSEEK_API_KEY=your_llm_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
# APIFY_API_KEY=...   # optional, currently not used for Instagram handles (now standard web scan)
```

### 4. Customize what you care about

Edit the two files created by `init`:

- `targets.json` — keywords, X/Instagram/etc handles (usernames), websites (full URLs). Instagram handles are scanned via direct profile URL fetch (whole profile) + web search fallback, like other social platforms. Private accounts yield whatever public data is available.
- `prompt.txt` — tone, length, priorities ("concise", "very detailed", etc.)

### 5. Test it

```bash
duga --dry-run
```

You will see what data it would collect (fresh live content) and the prompt it would send to the LLM.

When happy:

```bash
duga
```

This will generate a real briefing and send it via Telegram (and save a local copy with current fetch timestamps).

## Detailed Setup Instructions

### Telegram (required - use your own bot)

1. In Telegram search for **@BotFather**, send `/newbot`, follow prompts. Copy the token.
2. Paste into `TELEGRAM_BOT_TOKEN`.
3. Message your new bot at least once.
4. To get your Chat ID: message **@userinfobot** — it replies with the number. Paste into `TELEGRAM_CHAT_ID`.

### Instagram handles (standard web scan, no Apify)

Instagram usernames in `targets.json` are handled like other social platforms:
- Direct profile page fetch ("scan the whole profile at once" via https://instagram.com/handle/)
- Plus site-restricted web search fallback for posts/mentions.
- Private accounts: you get whatever is publicly crawlable ("oh well").
- No special Apify actor, no per-handle post limit, no private pre-skip.

The `APIFY_API_KEY` field is still accepted but not used for Instagram profile/post data.

### Other optional keys

- `BRAVE_API_KEY` / `TAVILY_API_KEY` — better web search
- Vision overrides (`VISION_*`) for image analysis

All keys and configs are stored only locally.

## Privacy

**Zero telemetry. Zero phoning home.**  
Only the connections you configure (LLM provider + Telegram + optionally Apify/Brave/etc.).

## Development

```bash
pip install -e ".[full]"
duga init
```

See `pyproject.toml`.

---

**Duga 1.1.1 'Berkut-AM'** — ready for daily use. Run the installer, configure once, let it run (in tray or via scheduler). All your data survives updates. Fresh content every time. Multiple named instances supported.

## Features

- Config-driven via simple JSON + text files (`targets.json` + `prompt.txt`)
- Web search + full website scraping + social profile scanning
- Optional vision analysis on images
- Uses DeepSeek-V4-Flash (fast & cheap) or swap models
- Remembers the last 14 days of briefings for continuity
- Sends via Telegram (easy to extend to Discord/email)
- Safe: skips if today's briefing already exists
- Cross platform (Windows, macOS, Linux)
- Adjustable daily run time (GMT/UTC)
- Multiple named instances (own targets/prompt per instance, shared keys) with sequential auto-run queueing
- GUI right-click Cut/Copy/Paste on prompt + direct+safe JSON editing for targets with reload/confirm

## Privacy

**This tool is private by design.**

- No telemetry
- No accounts
- No data is sent to the author or any central server
- The *only* external calls are the ones you configure:
  - DeepSeek (or another LLM you point it at)
  - Your Telegram bot (or whatever notifier you configure)

You can audit the code. Fork it. Run it air-gapped if you want (except for the LLM call).

## How to run it every day (configurable GMT time)

The time is adjustable in the GUI (enter e.g. 09:30 or 14:00 in the Time (GMT) field and click Set). It always runs in GMT/UTC.

### Windows (Task Scheduler) — Recommended for home machines

See detailed instructions in the "Scheduling" section below, or use:

```powershell
schtasks /create /sc daily /st 12:00 /tn "DugaBriefing" /tr "duga" /ru %USERNAME%
```

(Adjust /st HH:MM for your preferred GMT time.)

### macOS / Linux (cron or launchd)

Add to your crontab (`crontab -e`):

```cron
0 12 * * * /path/to/duga >> /path/to/duga-logs/cron.log 2>&1
```

(Adjust the path. Use `which duga` after installation.)

You can also use `duga --schedule` (requires `apscheduler`) if you prefer a long-running process.

**GUI users**: the built-in scheduler (with Auto-run checkbox) supports the adjustable time + multiple instances. No need for external scheduler if using the Windows app.

## How it works

1. Load `targets.json` + `prompt.txt`
2. Gather fresh data from web, websites, and public social profiles
3. (If many targets) Split into ~10-entry chunks (keywords + sites + handles). Gather + ask LLM per chunk.
4. Synthesize the chunk briefings + recent history into one final daily briefing.
5. Deliver via Telegram (also saved locally).

**DeepSeek-V4-Flash note**: The model advertises a 1M-token context window (max output 384k). In practice, quality and retrieval precision are best below ~200-250k tokens. Duga therefore defaults to feeding data in small ~10-entry chunks and synthesizing — this keeps every LLM call small and high-quality regardless of how many targets you track.

Everything runs on **your** machine.

## Command line

```bash
duga                 # generate + send now (uses 10-entry chunking by default)
duga --dry-run
duga --chunk-size 0          # disable chunking (single big LLM call)
duga --chunk-size 8          # use custom chunk size
duga init
duga --config-dir ~/my-other-profile --dry-run
```

For multiple instances you can point --config-dir directly at any folder (e.g. the ones created by the GUI under `instances/Name`). The GUI's "Main" uses the primary config dir; additional ones live under its `instances/` subfolder (each with own targets.json + prompt.txt, sharing the root .env keys). When multiple run at briefing time via GUI auto-run they execute one after another.

## Getting API Keys

- DeepSeek: https://platform.deepseek.com (recommended model: `deepseek-v4-flash`)
- Brave Search (optional): https://brave.com/search/api/
- Tavily (optional): https://tavily.com
- Vision override (optional, falls back to DeepSeek): any compatible OpenAI-style vision endpoint
- Apify (optional, not used for Instagram): https://apify.com (only if you need it for something else)

### Telegram Setup (required - you must use your own bot)

1. Open Telegram and search for **@BotFather**.
2. Start a chat and send `/newbot`.
3. Follow the prompts to name your bot (e.g. "MyDugaBot") and choose a username (must end with "bot", e.g. MyDugaBot).
4. BotFather will give you a **bot token** like `123456789:AAF...`. Paste this into the GUI under "Telegram Bot Token".
5. **Important**: Message your new bot at least once (e.g. say "hi") so it can send you messages.

### Getting Your Telegram Chat ID

1. Search for **@userinfobot** (or **@getmyid_bot**) in Telegram.
2. Start a chat with it.
3. It will immediately reply with your numeric **Chat ID** (something like 987654321).
4. Paste this into the GUI under "Your Telegram Chat ID".

The bot will only be able to message you if you have started a conversation with it first.

## Privacy

**Zero telemetry. Zero phoning home.**  
The only network calls are to the LLM provider and notification service *you* configure. Your configs and history live only on your disk.

## Development

```bash
pip install -e ".[full]"
duga init
```

See `pyproject.toml` (uses src layout + console script).

## Windows Desktop GUI (EXE) — 1.1.1 'Berkut-AM'

Native Windows GUI using pure **tkinter + ttk** (exactly the same style as your PFR Reactor Sizer project — Segoe UI, LabelFrames, Notebook tabs, clean native widgets).

- Version: 1.1.1 'Berkut-AM'
- Tabs: Prompt, Targets, API Keys & Telegram, Run & Schedule
- Edit prompt, keywords, websites (as URLs), and all social platforms (handles/usernames). Instagram handles are scanned via direct profile URL + web search (like other platforms; "whole profile at once", private profiles yield what they yield).
- Configure and save your API keys locally (LLM, Telegram bot, Apify, optional Brave/Tavily/Vision)
- Manual run + live log
- Checkbox + time field for automatic daily execution at configurable HH:MM GMT (app must stay running; can be minimized to tray)
- Right-click context menu (Cut/Copy/Paste/Select All) on the Prompt text area
- Targets tab supports both list editors and direct raw JSON editing with Reload from disk + confirmation before overwrite to protect external edits
- Multiple instances: click "New Instance" to name and create a dedicated folder under `instances/<name>/` (own prompt + targets per instance). Shared API keys (from root .env). Use the dropdown to switch instances for editing. Delete with confirmation.
- When Auto-run is enabled and briefing time arrives, all discovered instances (Main + any under instances/) are queued and executed sequentially one at a time.

### Quick start from source

```powershell
python windows\duga_gui.py
python windows\duga_gui.py --minimized
```

### Building for Installer (folder distribution, no standalone EXE)

```powershell
python windows\build_exe.py
```

This produces a distribution folder `dist\Duga\` (using PyInstaller's onedir mode) intended for packaging.

Then create the proper Windows installer:

1. Download **Inno Setup** (free): https://jrsoftware.org/isinfo.php
2. Open `windows\DugaInstaller.iss`
3. Compile → produces `dist\DugaSetup-1.1.1-Berkut-AM.exe`

The installer:
- Installs Duga as a proper application
- Adds Start Menu shortcuts
- Adds a startup entry (launches minimized to tray)
- Registers a real uninstaller in "Apps & features"
- Supports easy updates: just run the new installer while the old version is installed. It will automatically (and silently) remove the old version first, then install the new one over the same location. No need to manually uninstall.

See `windows/README.md` for full details on tray, icon, and installer.

No extra UI libraries required (no customtkinter).

## Android App (APK)

There is a full GUI app in `mobile/duga_kivy_app.py` that lets you:

- Edit `prompt.txt` in a nice text box
- Manage keywords, websites, and social handles (X, Instagram, LinkedIn, Facebook, Threads) with add/remove
- Enter and save your LLM API key + Telegram bot details
- Tap **Run Briefing Now** to execute the full pipeline from your phone

### Quick local test of the mobile GUI

```bash
pip install kivy
python mobile/duga_kivy_app.py
```

### Building the APK (defunct)

1. Install buildozer (best on Linux or WSL):
   ```bash
   pip install buildozer
   sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
   ```

2. Go to the mobile folder and build:
   ```bash
   cd mobile
   buildozer android debug
   ```

3. The APK will be in `mobile/bin/`. Install it on your Android device.

**Limitations on Android**:
- Background daily execution at exactly 12:00 GMT is restricted by Android (Doze, battery optimization).
- The app works great for manual runs + config editing.
- For reliable daily runs many users keep the Python version on a home computer or small server and use the phone app only for configuration.
- Scraping some social platforms (especially Facebook, Instagram, LinkedIn) can be limited without login cookies.

The mobile app stores its own copy of `targets.json`, `prompt.txt` and `.env` in the app's private storage.

Happy briefing!
