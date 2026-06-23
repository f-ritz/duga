"""
Duga Mobile - Android APK GUI (Kivy) - 0.2.0 "Berkut-B"

Features tabs for:
- Prompt editor (writes prompt.txt)
- Targets manager (keywords, websites, social handles per platform)
- API Keys & Telegram setup (writes .env-style file)
- Run Briefing (executes the full pipeline using the core duga logic)

Build to APK with Buildozer (see README section).

Run locally for testing:
    pip install kivy
    python mobile/duga_kivy_app.py
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.textinput import TextInput
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp

# Reuse as much as possible from the desktop package
try:
    from duga.config import load_targets as _load_targets, load_prompt as _load_prompt
    from duga.main import run_once as _run_once
    HAS_RADAR_CORE = True
except Exception:
    HAS_RADAR_CORE = False


def get_duga_data_dir() -> Path:
    """Mobile-friendly data dir. Falls back to current dir for testing."""
    try:
        from kivy.app import App as _App
        user_dir = Path(_App.get_running_app().user_data_dir) / "duga"
    except Exception:
        user_dir = Path.home() / ".duga_mobile"
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def load_targets() -> dict:
    p = get_duga_data_dir() / "targets.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    # Default template
    return {
        "keywords": ["AI agents"],
        "social": {"x": [], "instagram": [], "linkedin": [], "facebook": [], "threads": []},
        "websites": []
    }


def save_targets(data: dict) -> None:
    p = get_duga_data_dir() / "targets.json"
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_prompt() -> str:
    p = get_duga_data_dir() / "prompt.txt"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return "You are a concise, neutral daily briefing writer.\nFocus on high-signal developments only."


def save_prompt(text: str) -> None:
    (get_duga_data_dir() / "prompt.txt").write_text(text.strip(), encoding="utf-8")


def load_env_dict() -> dict:
    p = get_duga_data_dir() / ".env"
    data = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()
    return data


def save_env_dict(data: dict) -> None:
    lines = ["# Duga mobile configuration\n"]
    for k, v in data.items():
        lines.append(f"{k}={v}")
    (get_duga_data_dir() / ".env").write_text("\n".join(lines), encoding="utf-8")


class EditableList(BoxLayout):
    """Simple editable list widget for keywords, websites, handles."""
    def __init__(self, items: list[str], on_change, title: str = "", **kwargs):
        super().__init__(orientation="vertical", spacing=dp(4), size_hint_y=None, **kwargs)
        self.bind(minimum_height=self.setter("height"))
        self.on_change = on_change
        self.items = list(items)

        header = BoxLayout(size_hint_y=None, height=dp(30))
        header.add_widget(Label(text=title, bold=True, size_hint_x=0.7))
        self.add_widget(header)

        self.list_container = BoxLayout(orientation="vertical", size_hint_y=None)
        self.list_container.bind(minimum_height=self.list_container.setter("height"))
        self.add_widget(self.list_container)

        add_box = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        self.add_input = TextInput(hint_text="Add new item...", multiline=False, size_hint_x=0.7)
        add_btn = Button(text="Add", size_hint_x=0.3, on_press=self._add_item)
        add_box.add_widget(self.add_input)
        add_box.add_widget(add_btn)
        self.add_widget(add_box)

        self._refresh_list()

    def _refresh_list(self):
        self.list_container.clear_widgets()
        for item in self.items:
            row = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(6))
            row.add_widget(Label(text=item, size_hint_x=0.7, halign="left"))
            del_btn = Button(text="✕", size_hint_x=0.3, width=dp(40))
            del_btn.bind(on_press=lambda btn, it=item: self._remove_item(it))
            row.add_widget(del_btn)
            self.list_container.add_widget(row)

    def _add_item(self, _):
        val = self.add_input.text.strip()
        if val and val not in self.items:
            self.items.append(val)
            self.add_input.text = ""
            self._refresh_list()
            self.on_change(self.items)

    def _remove_item(self, item):
        if item in self.items:
            self.items.remove(item)
            self._refresh_list()
            self.on_change(self.items)


class DugaMobileApp(App):
    title = "Duga 0.2.0 \"Berkut-B\""

    def build(self):
        self.data_dir = get_duga_data_dir()
        self.targets = load_targets()
        self.prompt_text = load_prompt()
        self.env_data = load_env_dict()

        root = TabbedPanel(do_default_tab=False)

        # === TAB 1: Prompt ===
        prompt_tab = TabbedPanelItem(text="Prompt")
        prompt_layout = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        prompt_layout.add_widget(Label(text="Edit your briefing style (saved to prompt.txt)", size_hint_y=None, height=dp(30)))
        self.prompt_input = TextInput(text=self.prompt_text, multiline=True, size_hint_y=1)
        prompt_layout.add_widget(self.prompt_input)
        save_prompt_btn = Button(text="Save Prompt", size_hint_y=None, height=dp(48))
        save_prompt_btn.bind(on_press=self.save_prompt)
        prompt_layout.add_widget(save_prompt_btn)
        prompt_tab.add_widget(prompt_layout)
        root.add_widget(prompt_tab)

        # === TAB 2: Targets ===
        targets_tab = TabbedPanelItem(text="Targets")
        targets_scroll = ScrollView()
        targets_main = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(12), size_hint_y=None)
        targets_main.bind(minimum_height=targets_main.setter("height"))

        # Keywords
        self.keywords_list = EditableList(
            self.targets.get("keywords", []),
            on_change=lambda items: self._update_targets("keywords", items),
            title="Keywords"
        )
        targets_main.add_widget(self.keywords_list)

        # Websites
        self.websites_list = EditableList(
            self.targets.get("websites", []),
            on_change=lambda items: self._update_targets("websites", items),
            title="Websites (full URLs)"
        )
        targets_main.add_widget(self.websites_list)

        # Social platforms
        targets_main.add_widget(Label(text="Social Media Handles", bold=True, size_hint_y=None, height=dp(28)))

        social = self.targets.get("social", {})
        self.social_lists = {}
        for platform in ["x", "instagram", "linkedin", "facebook", "threads"]:
            lst = EditableList(
                social.get(platform, []),
                on_change=lambda items, p=platform: self._update_social(p, items),
                title=f"@{platform.capitalize()} handles"
            )
            targets_main.add_widget(lst)
            self.social_lists[platform] = lst

        targets_scroll.add_widget(targets_main)
        targets_tab.add_widget(targets_scroll)
        root.add_widget(targets_tab)

        # === TAB 3: API Keys ===
        keys_tab = TabbedPanelItem(text="Keys & Telegram")
        keys_layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        keys_layout.add_widget(Label(text="API Keys & Notification (saved locally)", size_hint_y=None, height=dp(30)))

        self.key_inputs = {}
        for key, hint in [
            ("DEEPSEEK_API_KEY", "LLM API Key"),
            ("TELEGRAM_BOT_TOKEN", "Telegram Bot Token"),
            ("TELEGRAM_CHAT_ID", "Your Telegram Chat/User ID"),
        ]:
            row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
            row.add_widget(Label(text=hint, size_hint_x=0.35))
            ti = TextInput(text=self.env_data.get(key, ""), password="KEY" in key, multiline=False)
            self.key_inputs[key] = ti
            row.add_widget(ti)
            keys_layout.add_widget(row)

        save_keys_btn = Button(text="Save API Keys", size_hint_y=None, height=dp(48), on_press=self.save_keys)
        keys_layout.add_widget(save_keys_btn)

        keys_layout.add_widget(Label(text="Note: Keys are stored only on this device.", size_hint_y=None, height=dp(30)))
        keys_tab.add_widget(keys_layout)
        root.add_widget(keys_tab)

        # === TAB 4: Run ===
        run_tab = TabbedPanelItem(text="Run")
        run_layout = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        run_layout.add_widget(Label(text="Generate a briefing now using your settings", size_hint_y=None, height=dp(30)))

        self.status_label = Label(text="Ready", size_hint_y=None, height=dp(30))
        run_layout.add_widget(self.status_label)

        run_btn = Button(text="▶ Run Briefing Now", size_hint_y=None, height=dp(60), background_color=(0.2, 0.6, 0.3, 1))
        run_btn.bind(on_press=self.run_briefing)
        run_layout.add_widget(run_btn)

        self.log_output = TextInput(text="Logs will appear here...", readonly=True, multiline=True, size_hint_y=1)
        run_layout.add_widget(self.log_output)

        run_layout.add_widget(Label(
            text="Note: Daily automatic runs on Android are limited by the OS.\n"
                 "Use 'Run Now' or pair with automation apps (Tasker, etc.).",
            size_hint_y=None, height=dp(60), font_size="12sp"
        ))
        run_tab.add_widget(run_layout)
        root.add_widget(run_tab)

        # Make sure we save targets on app close too
        return root

    def _update_targets(self, key: str, value: list):
        self.targets[key] = value
        save_targets(self.targets)

    def _update_social(self, platform: str, value: list):
        if "social" not in self.targets:
            self.targets["social"] = {}
        self.targets["social"][platform] = value
        save_targets(self.targets)

    def save_prompt(self, _btn):
        text = self.prompt_input.text.strip()
        save_prompt(text)
        self.status_label.text = "Prompt saved."
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', 'Ready'), 2)

    def save_keys(self, _btn):
        for k, ti in self.key_inputs.items():
            self.env_data[k] = ti.text.strip()
        save_env_dict(self.env_data)
        self.status_label.text = "Keys saved to device storage."
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', 'Ready'), 2)

    def append_log(self, msg: str):
        def _update(dt):
            self.log_output.text += "\n" + msg
            self.log_output.cursor = (0, len(self.log_output.text))
        Clock.schedule_once(_update)

    def run_briefing(self, _btn):
        self.status_label.text = "Running..."
        self.append_log("Starting briefing run...")

        def worker():
            try:
                # Make sure latest files are written
                save_targets(self.targets)
                save_prompt(self.prompt_input.text)
                save_env_dict(self.env_data)

                # Try to use the real core logic
                if HAS_RADAR_CORE:
                    # Force the desktop config to use our mobile dir for this run
                    import os
                    os.environ["DUGA_CONFIG_DIR"] = str(self.data_dir)

                    # Reload to pick up
                    import importlib
                    import duga.config as rcfg
                    importlib.reload(rcfg)

                    result = _run_once(dry_run=False, force=True)
                    self.append_log(f"Core run finished with code: {result}")
                else:
                    self.append_log("Core duga package not importable in this environment.")
                    self.append_log("In a packaged APK this should work.")

                # Basic fallback info
                self.append_log("Briefing generation attempted. Check your Telegram.")
            except Exception as e:
                self.append_log(f"ERROR: {e}")
            finally:
                Clock.schedule_once(lambda dt: setattr(self.status_label, "text", "Done."))

        threading.Thread(target=worker, daemon=True).start()

    def on_stop(self):
        # Persist everything
        save_targets(self.targets)
        save_prompt(self.prompt_input.text)
        save_env_dict(self.env_data)


if __name__ == "__main__":
    DugaMobileApp().run()
