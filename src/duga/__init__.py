"""Duga - Personal daily briefing agent.

A lightweight, fully local AI agent that gathers information from the web,
social profiles, and websites according to your targets, summarizes with
an LLM (DeepSeek by default), and delivers via Telegram.

Everything runs on your machine. Your data and configurations never leave
except for the API calls you explicitly configure (DeepSeek + Telegram).

Version: 0.1.0 "Berkut"
"""
__version__ = "0.1.0"
CODENAME = "Berkut"
DISPLAY_VERSION = f'{__version__} "{CODENAME}"'
