# Duga

**Duga 0.1.0 "Berkut" — Fully local personal daily briefing agent.**

Duga gathers information based on *your* keywords, social handles, and websites, summarizes the results with an LLM (DeepSeek by default), and sends you a concise briefing via Telegram.

- Everything runs **on your own computer**.
- Your `targets.json`, `prompt.txt`, briefings, and data stay **private** — the author of this project never sees anything.
- Designed to be easy for anyone to install and run for themselves.

## Quick Start (for normal users)

### 1. Install

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

### 3. Add your API keys

```bash
# Go to your config directory (duga init tells you the path)
cd "$(duga --help | grep -i config || echo "$HOME/.config/duga")"   # or manually
cp .env.example .env
```

Edit `.env` and fill in at minimum:

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

### 4. Customize what you care about

Edit the two files created by `init`:

- `targets.json` — keywords, X/Instagram/etc handles, websites
- `prompt.txt` — tone, length, priorities ("concise", "very detailed", etc.)

### 5. Test it

```bash
duga --dry-run
```

You will see what data it would collect and the prompt it would send to the LLM.

When happy:

```bash
duga
```

This will generate a real briefing and send it via Telegram (and save a local copy).

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
- Telegram bot + chat ID: @BotFather on Telegram

## Privacy

**Zero telemetry. Zero phoning home.**  
The only network calls are to the LLM provider and notification service *you* configure. Your configs and history live only on your disk.

## Development

```bash
pip install -e ".[full]"
duga init
```

See `pyproject.toml` (uses src layout + console script).

## Windows Desktop GUI (EXE) — 0.1.0 "Berkut"

Native Windows GUI using pure **tkinter + ttk** (exactly the same style as your PFR Reactor Sizer project — Segoe UI, LabelFrames, Notebook tabs, clean native widgets).

- Version: 0.1.0 "Berkut"
- Tabs: Prompt, Targets, API Keys & Telegram, Run & Schedule
- Edit prompt, keywords, websites, and all social platforms (x / instagram / linkedin / facebook / threads)
- Configure and save your API keys locally
- Manual run + live log
- Checkbox for automatic daily execution at 12:00 GMT (keep the window open or minimized)

### Quick start from source

```powershell
python windows\duga_gui.py
python windows\duga_gui.py --minimized
```

### Building the EXE + Real Installer

```powershell
python windows\build_exe.py
```

Then create a proper installable program:

1. Download **Inno Setup** (free): https://jrsoftware.org/isinfo.php
2. Open `windows\DugaInstaller.iss`
3. Compile → produces `dist\DugaSetup-0.1.0-Berkut.exe`

The installer adds Start Menu shortcuts, a startup entry (launches to tray), and a real uninstaller in "Apps & features".

See `windows/README.md` for full details on tray, icon, and installer.

Result: single-file `dist\Duga.exe`

No extra UI libraries required (no customtkinter).

You can place this EXE anywhere on your laptop. Just double-click it, configure everything, enable "Auto-run daily...", and leave the window open (or minimized).

See `windows/README.md` for more details.

## Android App (APK)

There is a full GUI app in `mobile/duga_kivy_app.py` that lets you:

- Edit `prompt.txt` in a nice text box
- Manage keywords, websites, and social handles (X, Instagram, LinkedIn, Facebook, Threads) with add/remove
- Enter and save your DeepSeek API key + Telegram bot details
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
