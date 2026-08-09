# Duga Mobile (Android) — 1.1.1 'Berkut-AM'

Companion GUI built with **Kivy** for **Duga 1.1.1 'Berkut-AM'**.

Use it to manage configuration from your phone and trigger a full briefing run when the core package is available (e.g. inside the APK).

---

## What the mobile app does

| Tab | Purpose |
|-----|---------|
| **Prompt** | Edit briefing style instructions → `prompt.txt` |
| **Targets** | Keywords, websites, social handles (X, Instagram, LinkedIn, Facebook, Threads) with add/remove lists |
| **Keys & Telegram** | LLM API key + Telegram bot token + chat ID (and related fields) → local `.env`-style storage |
| **Run** | One-tap **▶ Run Briefing Now** — runs the same gather → LLM → Telegram pipeline as desktop when core is bundled |

### Gathering & delivery (same core as desktop)

When “Run Briefing Now” executes with the Duga core present:

1. Load targets + prompt + keys from the app data directory  
2. Web search (DuckDuckGo), website scrapes, social profile scans  
3. Optional vision on collected media  
4. Chunked LLM briefings (default) + synthesis, with 14-day history context  
5. Save local briefing + send via your Telegram bot  

Instagram handles use direct profile URL scan + search (no Apify). Other platforms match desktop behavior. See the root [README.md](../README.md) for full pipeline details.

---

## Features aligned with 1.1.1

- Full target types: keywords, websites, multi-platform social handles  
- Local-only credentials (never sent to the project author)  
- Manual full pipeline run from the phone  
- Private app storage for `targets.json`, `prompt.txt`, and keys  
- Portrait-oriented APK packaging via Buildozer  

**Not on mobile (desktop GUI only in 1.1.1):**

- System tray / minimize-to-background productization  
- Multi-instance folders + sequential auto-run queue  
- Adjustable GMT auto-run UI + `settings.json` controls  
- Advanced raw JSON targets editor with overwrite confirm  
- Windows installer  

For reliable daily automatic runs, use the Windows GUI or CLI scheduler on a computer, and use this app for editing + on-demand runs.

---

## Data location on device

The app stores configuration under its private user data directory (Kivy `user_data_dir` / `duga`), including:

- `targets.json`
- `prompt.txt`
- `.env` (or equivalent key storage)

This data stays on the device. It is not shared with the author.

For desktop parity, export or copy these files and point the CLI/GUI at them with:

```bash
# Windows example
set DUGA_CONFIG_DIR=C:\path\to\exported\config
duga --dry-run
```

(`RADAR_CONFIG_DIR` is still accepted as a legacy alias.)

---

## Quick local test (desktop / emulator host)

```bash
pip install kivy
# from repo root, with package importable:
pip install -e .
python mobile/duga_kivy_app.py
```

Without the installed `duga` package, the UI still loads for editing; full **Run** needs the core modules.

---

## Building the APK

Best on **Linux or WSL**.

1. Install Buildozer and Android build deps (example for Debian/Ubuntu-style systems):

   ```bash
   pip install buildozer
   sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool \
     pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
   ```

2. Build from the mobile folder:

   ```bash
   cd mobile
   buildozer android debug
   ```

3. Install the APK from `mobile/bin/` on your device.

`buildozer.spec` notes for 1.1.1:

- `version = 1.1.1`
- Package name: `duga`
- Requirements include the core stack (requests, openai, trafilatura, duckduckgo-search, etc.)
- Includes `src/duga/*.py` and templates so **Run Now** can execute the real pipeline
- Permissions: `INTERNET` (+ storage as declared)
- Arch: `arm64-v8a`, min API 21

---

## Limitations on Android

- **Background daily scheduling** at a fixed GMT time is restricted by Doze / battery optimization. Exact auto-run is not productized here the way the Windows tray app is.
- Scraping some social platforms (Facebook, Instagram, LinkedIn) can be limited without login cookies or may be rate-limited on mobile networks.
- Long runs need a stable network and enough time before the OS freezes background work.
- Practical pattern: phone for config + manual briefings; desktop/server for hands-off daily delivery.

---

## Related docs

- Product overview, CLI, env vars, privacy: [../README.md](../README.md)  
- Windows GUI + installer: [../windows/README.md](../windows/README.md)  
