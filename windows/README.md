# Duga Windows GUI + Installer (EXE) — 1.1.1 'Berkut-AM'

**Duga 1.1.1 'Berkut-AM'**

Native Windows desktop app for Duga: pure **tkinter + ttk** (Segoe UI, LabelFrames, Notebook tabs). Wraps the full core pipeline (gather → LLM → Telegram) with tray support, auto-run, multi-instance configs, and a proper installer.

Version codename: **Berkut-AM**

---

## What the Windows app does

Everything the core agent does, plus a full desktop control surface:

| Capability | Behavior |
|------------|----------|
| **Edit prompt** | Saves `prompt.txt` for the active instance |
| **Edit targets** | Keywords, websites, social handles (X, Instagram, LinkedIn, Facebook, Threads) with add/remove lists |
| **Advanced JSON targets** | Edit `targets.json` raw; Reload from disk; Validate & Save; confirm if file changed externally |
| **API keys** | Local `.env` only (DeepSeek, Telegram, optional vision / reserved fields) |
| **Run now** | Full briefing pipeline for the **current** instance (`force=True` so it always re-runs) |
| **Auto-run** | Daily at configurable **HH:MM GMT/UTC** while the process is alive (including tray) |
| **Multi-instance auto-run** | At fire time, queues **Main + every folder under `instances/`** and runs them **sequentially** |
| **Chunk size** | Adjustable; `0` = single LLM pass; default `10` |
| **IG posts/profile** | Setting stored in `settings.json` (compat / token control UI; IG gather is URL+search based) |
| **System tray** | Close (X) hides to tray; double-click restores; right-click menu |
| **Startup** | Installer can add Startup shortcut with `--minimized` |

Shared across instances: **API keys** (root `.env`). Per instance: **`targets.json`**, **`prompt.txt`**, and that instance’s briefings/logs when run with its config dir.

---

## Features in 1.1.1 'Berkut-AM'

- Application icon (`icon.ico` / `radar.ico`) on window, taskbar, EXE, tray
- Minimize to system tray on close (not quit)
- Tray menu: **Show**, **Run Briefing Now**, **Exit**
- Double-click tray icon → restore window
- `--minimized` / `--tray` CLI flags for clean startup
- Adjustable auto-run time (HH:MM GMT + **Set**)
- Adjustable chunk size + IG posts/profile controls (persisted in `settings.json`)
- Right-click **Cut / Copy / Paste / Select All** on Prompt and JSON editors
- Targets tab advanced JSON editor with reload + overwrite protection
- **New Instance** / **Delete Instance…** / instance dropdown
- Sequential multi-instance queue on auto-run
- Inno Setup installer → Apps & features, Start Menu, Startup, silent upgrades

---

## GUI map

### Top / status bars
- Title: `Duga 1.1.1 "Berkut-AM"` (or display version from core)
- **▶ Run Briefing Now**
- Config path status
- **Auto-run daily at configured time GMT** checkbox
- **Time (GMT)** + Set
- **Chunk size** + Set
- **IG posts/profile** + Set

### Instance bar
- Combobox (Main + named instances)
- **New Instance** — creates `instances/<safe_name>/` with default targets + prompt
- **Delete Instance…** — removes that folder (Main cannot be deleted)

### Tabs

1. **Prompt** — style instructions → `prompt.txt`
2. **Targets**
   - Keywords list
   - Websites (full `https://` URLs)
   - Social handles (usernames only): X, Instagram (URL + search scan), LinkedIn, Facebook, Threads
   - Advanced: raw JSON + Reload / Validate & Save / Sync from Lists
3. **API Keys & Telegram**
   - `DEEPSEEK_API_KEY` (required)
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (required for delivery)
   - Optional / reserved: `APIFY_API_KEY` (not used for IG in 1.1.1), `BRAVE_API_KEY`, `TAVILY_API_KEY`, `VISION_API_KEY`, `VISION_BASE_URL`, `VISION_MODEL`
4. **Run & Schedule** — status, run button, activity log

### Tray behavior
| Action | Result |
|--------|--------|
| Click window **X** | Hide to tray (app keeps running; auto-run continues) |
| Double-click tray icon | Show main window |
| Right-click → Show | Show main window |
| Right-click → Run Briefing Now | Run current instance immediately |
| Right-click → Exit | Fully quit |

---

## Data locations

| What | Where |
|------|--------|
| User config (keys, main targets/prompt, settings, briefings) | Platform config dir via core, typically `%APPDATA%\duga` |
| Named instances | `%APPDATA%\duga\instances\<Name>\` |
| Installed app binaries | `%LocalAppData%\Duga` (installer default) |
| Settings (time, chunk, IG limit) | `settings.json` in main data dir |

Override data dir with env `DUGA_CONFIG_DIR` (or legacy `RADAR_CONFIG_DIR`).

The CLI `duga` command and this GUI share the same config files when pointed at the same directory.

---

## Running from source

```powershell
# From repo root (with duga package importable, e.g. pip install -e .)
python windows\duga_gui.py
python windows\duga_gui.py --minimized
```

**Tray dependency (dev / full tray):**

```powershell
pip install pywin32
```

Without `pywin32`, the GUI still runs; tray features are limited/disabled.

---

## Building the distribution (for installer)

```powershell
python windows\build_exe.py
```

Requires: PyInstaller + `pywin32` for tray.

Produces a **folder** distribution at `dist\Duga\` (PyInstaller **onedir** mode). This is intentionally not a single-file portable EXE — it is meant to be packaged by the installer.

---

## Creating the installer

1. Download & install **Inno Setup 6+**: https://jrsoftware.org/isinfo.php  
2. Build the app first (`python windows\build_exe.py`).  
3. Open `windows\DugaInstaller.iss`.  
4. Compile (F9) → `dist\DugaSetup-1.1.1-Berkut-AM.exe`.

### What the installer does

- Installs to `%LocalAppData%\Duga`
- Start Menu shortcuts (app + uninstall)
- Startup entry: `Duga.exe --minimized` (tray on login)
- Registers uninstaller in **Apps & features**
- **In-place updates**: running a newer installer silently uninstalls the previous version first (same AppId), then installs over the same location
- `CloseApplications` helps stop a running/tray Duga before upgrade

User config under `%APPDATA%\duga` is **not** wiped by normal app updates.

---

## Icon

Place `icon.ico` (recommended multi-size 16/32/48/256) in the project root before building. `radar.ico` is also accepted as a fallback name.

Used for:

- EXE icon  
- Window title bar / taskbar  
- System tray icon  

---

## Pipeline behavior from the GUI

When you run (manual or auto):

1. Saves current instance prompt/targets (if it’s the active instance) and keys.
2. Injects env vars + sets `DUGA_CONFIG_DIR` to that instance’s folder.
3. Calls core `run_once(..., force=True, chunk_size=…, …)`.
4. Core: gather (DuckDuckGo + scrapes + social) → optional vision → chunked LLM (default) → save briefing → Telegram.
5. Auto-run path loops all instances with a short pause between each.

See the root [README.md](../README.md) for gather/LLM/Telegram details and environment variables.

---

## Persistence after install

With installer + Startup shortcut, Duga launches minimized to the tray on login. Enable Auto-run and set your GMT time once; leave it running in the tray for daily briefings across all instances.

You can still use the `duga` CLI (if installed via pip) against the same data directory for dry-runs, force runs, or automation.
