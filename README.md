# Duga

**Duga 1.0.0 "Berkut-M" — Fully local personal daily briefing agent.**

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
APIFY_API_KEY=your_apify_token_here   # for Instagram
```

### 4. Customize what you care about

Edit the two files created by `init`:

- `targets.json` — keywords, X/Instagram/etc handles (usernames), websites (full URLs). Instagram handles are scanned via Apify for rich profile + post data.
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

### Apify for Instagram (recommended for real data)

1. Sign up at https://apify.com and get your API token.
2. Paste into `APIFY_API_KEY`.
3. In `targets.json` under `"instagram"` put usernames (handles only).
4. The `apify/instagram-scraper` actor will fetch live profile info + recent posts/reels (bio, followers, captions, likes, comments, views, hashtags, mentions, locations, etc.).
5. This rich data is formatted and fed into the LLM for the daily briefing (alongside web search, other social, and website content).

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

**Duga 1.0.0 "Berkut-M"** — ready for daily use. Run the installer, configure once, let it run (in tray or via scheduler). All your data survives updates. Fresh content every time.

## Features

- Config-driven via simple JSON + text files (`targets.json` + `prompt.txt`)
- Web search + full website scraping + social profile scanning
- Optional vision analysis on images
- Uses DeepSeek-V4-Flash (fast & cheap) or swap models
- Remembers the last 14 days of briefings for continuity
- Sends via Telegram (easy to extend to Discord/email)
- Safe: skips if today's briefing already exists
- Cross platform (Windows, macOS, Linux)

## Privacy

**This tool is private by design.**

- No telemetry
- No accounts
- No data is sent to the author or any central server
- The *only* external calls are the ones you configure:
  - DeepSeek (or another LLM you point it at)
  - Your Telegram bot (or whatever notifier you configure)

You can audit the code. Fork it. Run it air-gapped if you want (except for the LLM call).

## How to run it every day (12:00 GMT / UTC)

### Windows (Task Scheduler) — Recommended for home machines

See detailed instructions in the "Scheduling" section below, or use:

```powershell
schtasks /create /sc daily /st 12:00 /tn "DugaBriefing" /tr "duga" /ru %USERNAME%
```

### macOS / Linux (cron or launchd)

Add to your crontab (`crontab -e`):

```cron
0 12 * * * /path/to/duga >> /path/to/duga-logs/cron.log 2>&1
```

(Adjust the path. Use `which duga` after installation.)

You can also use `duga --schedule` (requires `apscheduler`) if you prefer a long-running process.

## How it works

1. Load `targets.json` + `prompt.txt`
2. Gather fresh data from web, websites, and public social profiles
3. Send collected data + last 14 briefings + your style instructions to the LLM
4. Receive the briefing and deliver it via Telegram (also saved locally)

Everything runs on **your** machine.

## Command line

```bash
duga                 # generate + send now
duga --dry-run
duga init
duga --config-dir ~/my-other-profile --dry-run
```

## Getting API Keys

- DeepSeek: https://platform.deepseek.com (recommended model: `deepseek-v4-flash`)
- Apify (for Instagram scraping): https://apify.com (create account + get API token).  
  The app is designed around the official actor **apify/instagram-scraper** (https://apify.com/apify/instagram-scraper).  
  In `targets.json` you put usernames under the `"instagram"` key (e.g. `"instagram": ["cristiano", "nasa"]`).  
  When you provide an `APIFY_API_KEY`, the gather step will run this actor to fetch real profile data + recent posts/reels instead of (or in addition to) weak web search results. The output gets passed to the LLM for the daily briefing.
- Brave Search (optional): https://brave.com/search/api/
- Tavily (optional): https://tavily.com
- Vision override (optional, falls back to DeepSeek): any compatible OpenAI-style vision endpoint

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

## Windows Desktop GUI (EXE) — 1.0.0 "Berkut-M"

Native Windows GUI using pure **tkinter + ttk** (exactly the same style as your PFR Reactor Sizer project — Segoe UI, LabelFrames, Notebook tabs, clean native widgets).

- Version: 1.0.0 "Berkut-M"
- Tabs: Prompt, Targets, API Keys & Telegram, Run & Schedule
- Edit prompt, keywords, websites (as URLs), and all social platforms (handles/usernames). For Instagram, you list usernames in targets.json → they get fed to the `apify/instagram-scraper` actor (if you provide an APIFY_API_KEY) so richer profile + post data is included for the LLM.
- Configure and save your API keys locally (LLM, Telegram bot, Apify, optional Brave/Tavily/Vision)
- Manual run + live log
- Checkbox for automatic daily execution at 12:00 GMT (app must stay running; can be minimized to tray)

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
3. Compile → produces `dist\DugaSetup-1.0.0-Berkut-M.exe`

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

### Building the APK

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
