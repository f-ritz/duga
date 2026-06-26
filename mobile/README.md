# Duga Mobile (Android)

This is a companion GUI app built with Kivy for Duga 1.0.0 "Berkut-M".

It lets you comfortably manage everything from your phone:

- Prompt style
- All targets (keywords + websites + social across X / Instagram / LinkedIn / Facebook / Threads)
- Your API keys and Telegram details
- One-tap "Run Briefing Now"

## Building the APK

See the main project README for build instructions using Buildozer.

After building, the APK will contain the full duga logic, so "Run Now" will actually perform searches, call DeepSeek, and send to Telegram.

## Data location on device

The app stores `targets.json`, `prompt.txt` and `.env` inside its private app data directory. This data is not shared with the author.

You can also use the desktop `radar` tool with `RADAR_CONFIG_DIR` pointing at an exported copy if you want the same settings on both.
