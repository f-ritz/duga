"""
Duga Windows GUI - Desktop EXE version (pure tkinter + ttk)

Radar 0.1.0 "Berkut"

Matches the clean native Windows style from the PFR Reactor Sizer project
(Segoe UI, ttk widgets, LabelFrames, Notebook tabs).

Features added:
- Application icon support (icon.ico)
- Minimize to system tray on close (X)
- Full tray icon with right-click menu (Show, Run Briefing Now, Exit)
- Double-click tray to restore
- --minimized command line support (for startup)
- Designed to run in background like a normal app

Version: 0.1.0 "Berkut"

Requirements for tray:
    pip install pywin32   # only needed for development / full tray

Run:
    python windows\radar_gui.py
    python windows\radar_gui.py --minimized

Build EXE:
    python windows\build_exe.py
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional

# --- Robust path handling (PFR style) --------------------------------------
def _ensure_duga_on_path():
    here = Path(__file__).resolve()
    for ancestor in [here.parent] + list(here.parents):
        if (ancestor / "src" / "duga" / "__init__.py").is_file():
            if str(ancestor) not in sys.path:
                sys.path.insert(0, str(ancestor))
            return
        if (ancestor / "duga" / "__init__.py").is_file():
            if str(ancestor) not in sys.path:
                sys.path.insert(0, str(ancestor))
            return
    fallback = here.parent.parent
    if str(fallback) not in sys.path:
        sys.path.insert(0, str(fallback))

_ensure_duga_on_path()
# ---------------------------------------------------------------------------

import tkinter as tk
from tkinter import ttk, messagebox

# Optional tray support (Windows only)
HAS_TRAY = False
try:
    import win32gui
    import win32con
    import win32api
    HAS_TRAY = True
except ImportError:
    pass

# Try duga core
try:
    from duga import DISPLAY_VERSION, __version__
    from duga.config import get_config_dir
    from duga.main import run_once as _run_once
    HAS_RADAR_CORE = True
    APP_VERSION = DISPLAY_VERSION
except Exception:
    HAS_RADAR_CORE = False
    APP_VERSION = '0.1.0 "Berkut"'


def get_data_dir() -> Path:
    if HAS_RADAR_CORE:
        try:
            d = get_config_dir()
            d.mkdir(parents=True, exist_ok=True)
            return d
        except Exception:
            pass
    base = Path(os.getenv("DUGA_CONFIG_DIR", Path.home() / ".duga"))
    base.mkdir(parents=True, exist_ok=True)
    return base


DATA_DIR = get_data_dir()
TARGETS_FILE = DATA_DIR / "targets.json"
PROMPT_FILE = DATA_DIR / "prompt.txt"
ENV_FILE = DATA_DIR / ".env"
ICON_NAME = "icon.ico"


def load_targets() -> dict:
    if TARGETS_FILE.exists():
        try:
            return json.loads(TARGETS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "keywords": ["AI agents", "xAI"],
        "social": {"x": [], "instagram": [], "linkedin": [], "facebook": [], "threads": []},
        "websites": []
    }


def save_targets(data: dict) -> None:
    TARGETS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_prompt() -> str:
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8").strip()
    return "You are a concise, neutral daily intelligence briefer.\nFocus on high-signal developments only."


def save_prompt(text: str) -> None:
    PROMPT_FILE.write_text(text.strip(), encoding="utf-8")


def load_env_dict() -> Dict[str, str]:
    data: Dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = [x.strip() for x in line.split("=", 1)]
                data[k] = v
    return data


def save_env_dict(data: Dict[str, str]) -> None:
    lines = ["# Radar configuration\n"]
    for k, v in data.items():
        lines.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------- Native Editable List (ttk style) -----------------
class EditableList(ttk.Frame):
    """Simple native list control using Listbox + ttk (PFR style)."""

    def __init__(self, master: tk.Widget, title: str, items: List[str], on_change: Callable[[List[str]], None]):
        super().__init__(master)
        self.on_change = on_change
        self.items: List[str] = list(items)

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(2, 2))
        ttk.Label(header, text=title, font=("Segoe UI", 10, "bold")).pack(side="left")

        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(list_frame, height=5, exportselection=False, font=("Segoe UI", 9))
        self.listbox.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=sb.set)

        add_row = ttk.Frame(self)
        add_row.pack(fill="x", pady=2)
        self.entry = ttk.Entry(add_row)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(add_row, text="Add", width=8, command=self._add).pack(side="right")

        ttk.Button(self, text="Remove Selected", command=self._remove_selected).pack(fill="x", pady=2)

        self._refresh()

    def _refresh(self):
        self.listbox.delete(0, "end")
        for item in self.items:
            self.listbox.insert("end", item)

    def _add(self):
        val = self.entry.get().strip()
        if val and val not in self.items:
            self.items.append(val)
            self.entry.delete(0, "end")
            self._refresh()
            self.on_change(self.items)

    def _remove_selected(self):
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            del self.items[idx]
            self._refresh()
            self.on_change(self.items)

    def get_items(self) -> List[str]:
        return self.items


# ----------------------------- System Tray ----------------------------------
class SystemTray:
    """Windows system tray using pywin32 (reliable for EXE)."""

    def __init__(self, app: "RadarApp", icon_path: Optional[str], title: str):
        self.app = app
        self.icon_path = icon_path
        self.title = title
        self.hwnd = None
        self.notify_id = None

    def _get_hwnd(self):
        # Use Tk's window as message window
        if self.hwnd is None:
            self.hwnd = self.app.root.winfo_id()
        return self.hwnd

    def show_icon(self):
        if not HAS_TRAY or not self.icon_path or not os.path.exists(self.icon_path):
            return

        hwnd = self._get_hwnd()
        icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
        hicon = win32gui.LoadImage(0, self.icon_path, win32con.IMAGE_ICON, 0, 0, icon_flags)

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (hwnd, 0, flags, win32con.WM_USER + 20, hicon, self.title)

        if self.notify_id is None:
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
            self.notify_id = nid
        else:
            win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)

        # Register for left/right click
        win32gui.SetWindowLong(hwnd, win32con.GWL_WNDPROC, self._wnd_proc)

    def remove_icon(self):
        if self.notify_id and HAS_TRAY:
            hwnd = self._get_hwnd()
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, self.notify_id)
            self.notify_id = None

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if lparam == win32con.WM_LBUTTONDBLCLK:
            self.app.show_window()
        elif lparam == win32con.WM_RBUTTONUP:
            self._show_menu(hwnd)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _show_menu(self, hwnd):
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1, "Show Radar")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 2, "Run Briefing Now")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 3, "Exit")

        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(hwnd)
        cmd = win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_BOTTOMALIGN | win32con.TPM_RETURNCMD,
            pos[0], pos[1], 0, hwnd, None
        )
        win32gui.DestroyMenu(menu)

        if cmd == 1:
            self.app.show_window()
        elif cmd == 2:
            self.app.run_now_from_tray()
        elif cmd == 3:
            self.app.exit_from_tray()


# ------------------------------ Main App ------------------------------------
class RadarApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Radar {APP_VERSION}")
        self.root.geometry("780x620")
        self.root.minsize(720, 560)

        self.data_dir = DATA_DIR
        self.targets = load_targets()
        self.prompt_text = load_prompt()
        self.env_data = load_env_dict()
        self.auto_run_enabled = False
        self.last_run_date = None
        self.tray: Optional[SystemTray] = None

        self._set_window_icon()
        self._build_ui()

        # Tray setup
        if HAS_TRAY:
            icon_path = self._find_icon_path()
            self.tray = SystemTray(self, icon_path, f"Radar {APP_VERSION}")
            # Start with tray icon visible
            self.tray.show_icon()

        # Close button → minimize to tray
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        # Handle command line (e.g. from startup shortcut)
        if "--minimized" in sys.argv or "--tray" in sys.argv:
            self.root.after(100, self.minimize_to_tray)

        # Scheduler thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()

    def _find_icon_path(self) -> Optional[str]:
        """Find icon.ico in dev or frozen locations (PFR style)."""
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.append(os.path.join(getattr(sys, "_MEIPASS", ""), ICON_NAME))
        here = Path(__file__).resolve()
        for ancestor in [here.parent] + list(here.parents):
            candidates.append(str(ancestor / ICON_NAME))
            if (ancestor / "src" / "radar").exists():
                break
        for p in candidates:
            if os.path.isfile(p):
                return p
        return None

    def _set_window_icon(self):
        """Set taskbar + title bar icon (adapted from PFR project)."""
        icon_path = self._find_icon_path()
        if not icon_path:
            return
        try:
            self.root.iconbitmap(icon_path)
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("duga.daily.briefing.v1")
            except Exception:
                pass
        except Exception:
            pass

    def _build_ui(self):
        # Top bar
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")

        title = ttk.Label(top, text=f"Duga {APP_VERSION}", font=("Segoe UI", 13, "bold"))
        title.pack(side="left")

        self.btn_run = ttk.Button(top, text="▶ Run Briefing Now", command=self.run_now)
        self.btn_run.pack(side="right", padx=4)

        # Status
        status_bar = ttk.Frame(self.root, padding=(8, 2))
        status_bar.pack(fill="x")
        self.status_label = ttk.Label(status_bar, text=f"Config: {self.data_dir}")
        self.status_label.pack(side="left")

        self.auto_var = tk.BooleanVar(value=False)
        auto_cb = ttk.Checkbutton(
            status_bar,
            text="Auto-run daily at 12:00 GMT (keep window open)",
            variable=self.auto_var,
            command=self._toggle_auto,
        )
        auto_cb.pack(side="right")

        # Tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=8, pady=4)

        # PROMPT
        prompt_tab = ttk.Frame(notebook, padding=10)
        notebook.add(prompt_tab, text="Prompt")
        ttk.Label(prompt_tab, text="Style instructions (saved to prompt.txt)", font=("Segoe UI", 10)).pack(anchor="w")
        self.prompt_text_widget = tk.Text(prompt_tab, height=18, wrap="word", font=("Segoe UI", 10))
        self.prompt_text_widget.pack(fill="both", expand=True, pady=4)
        self.prompt_text_widget.insert("1.0", self.prompt_text)
        ttk.Button(prompt_tab, text="Save Prompt", command=self.save_prompt).pack(anchor="e")

        # TARGETS
        targets_tab = ttk.Frame(notebook, padding=8)
        notebook.add(targets_tab, text="Targets")

        self.kw_list = EditableList(targets_tab, "Keywords", self.targets.get("keywords", []),
                                    lambda items: self._update_targets("keywords", items))
        self.kw_list.pack(fill="x", pady=4)

        self.web_list = EditableList(targets_tab, "Websites (full URLs)", self.targets.get("websites", []),
                                     lambda items: self._update_targets("websites", items))
        self.web_list.pack(fill="x", pady=8)

        social_frame = ttk.LabelFrame(targets_tab, text="Social Handles", padding=6)
        social_frame.pack(fill="both", expand=True, pady=4)

        social = self.targets.get("social", {})
        self.social_lists: Dict[str, EditableList] = {}
        for plat in ["x", "instagram", "linkedin", "facebook", "threads"]:
            lst = EditableList(social_frame, plat.capitalize(), social.get(plat, []),
                               lambda items, p=plat: self._update_social(p, items))
            lst.pack(fill="x", pady=2)
            self.social_lists[plat] = lst

        # KEYS
        keys_tab = ttk.Frame(notebook, padding=10)
        notebook.add(keys_tab, text="API Keys & Telegram")
        ttk.Label(keys_tab, text="Credentials (stored only locally in .env)", font=("Segoe UI", 10)).pack(anchor="w", pady=4)

        self.key_entries: Dict[str, ttk.Entry] = {}
        for key, label in [
            ("DEEPSEEK_API_KEY", "DeepSeek API Key"),
            ("TELEGRAM_BOT_TOKEN", "Telegram Bot Token"),
            ("TELEGRAM_CHAT_ID", "Your Telegram Chat ID"),
        ]:
            row = ttk.Frame(keys_tab)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=22).pack(side="left")
            show = "*" if "KEY" in key or "TOKEN" in key else ""
            entry = ttk.Entry(row, width=50, show=show)
            entry.pack(side="left", fill="x", expand=True)
            entry.insert(0, self.env_data.get(key, ""))
            self.key_entries[key] = entry

        ttk.Button(keys_tab, text="Save Keys", command=self.save_keys).pack(anchor="e", pady=8)

        # RUN
        run_tab = ttk.Frame(notebook, padding=10)
        notebook.add(run_tab, text="Run & Schedule")

        self.run_status = ttk.Label(run_tab, text="Ready", font=("Segoe UI", 10))
        self.run_status.pack(anchor="w", pady=4)

        ttk.Button(run_tab, text="▶ Run Briefing Now", command=self.run_now).pack(fill="x", pady=6)

        ttk.Label(run_tab, text="Activity Log", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 2))
        self.log_widget = tk.Text(run_tab, height=12, state="disabled", font=("Consolas", 9))
        self.log_widget.pack(fill="both", expand=True)

        self.log(f"Radar {APP_VERSION} started.")
        self.log(f"Data dir: {self.data_dir}")

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_widget.configure(state="normal")
        self.log_widget.insert("end", f"[{ts}] {msg}\n")
        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

    def _update_targets(self, key: str, items: List[str]):
        self.targets[key] = items
        save_targets(self.targets)

    def _update_social(self, platform: str, items: List[str]):
        if "social" not in self.targets:
            self.targets["social"] = {}
        self.targets["social"][platform] = items
        save_targets(self.targets)

    def save_prompt(self):
        text = self.prompt_text_widget.get("1.0", "end").strip()
        save_prompt(text)
        self.run_status.configure(text="Prompt saved.")
        self.log("Prompt saved.")

    def save_keys(self):
        for k, entry in self.key_entries.items():
            self.env_data[k] = entry.get().strip()
        save_env_dict(self.env_data)
        self.run_status.configure(text="Keys saved.")
        self.log("Keys saved.")

    def _toggle_auto(self):
        self.auto_run_enabled = self.auto_var.get()
        self.log("Auto-run " + ("ENABLED" if self.auto_run_enabled else "DISABLED") + ".")

    def minimize_to_tray(self):
        self.root.withdraw()
        if self.tray:
            self.tray.show_icon()
        self.log("Minimized to tray.")

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        if self.tray:
            self.tray.remove_icon()

    def run_now(self):
        self.run_status.configure(text="Running...")
        threading.Thread(target=self._perform_briefing, daemon=True).start()

    def run_now_from_tray(self):
        self.log("Run triggered from tray.")
        self._perform_briefing()

    def _perform_briefing(self):
        self.log("Starting briefing...")
        try:
            self.save_prompt()
            self.save_keys()
            save_targets(self.targets)

            if HAS_RADAR_CORE:
                os.environ["DUGA_CONFIG_DIR"] = str(self.data_dir)
                import importlib
                import duga.config as rcfg
                importlib.reload(rcfg)
                code = _run_once(dry_run=False, force=True)
                self.log(f"Completed (exit {code}). Check Telegram.")
            else:
                self.log("Core not available in this session (full in EXE).")

            self.run_status.configure(text="Done.")
        except Exception as e:
            self.log(f"ERROR: {e}")
            self.run_status.configure(text="Error")

    def exit_from_tray(self):
        if self.tray:
            self.tray.remove_icon()
        self.root.destroy()

    def _scheduler_loop(self):
        while True:
            try:
                time.sleep(25)
                if not self.auto_run_enabled:
                    continue
                now = datetime.now(timezone.utc)
                if now.hour == 12 and now.minute < 1:
                    today = now.date().isoformat()
                    if self.last_run_date != today:
                        self.last_run_date = today
                        self.log("Auto 12:00 GMT run...")
                        self._perform_briefing()
            except Exception:
                time.sleep(60)

    def on_closing(self):
        # Already handled by protocol, but safe
        self.minimize_to_tray()


def main():
    root = tk.Tk()
    app = RadarApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
