"""Duga - Personal daily briefing agent.

A lightweight, fully local AI agent that gathers information from the web,
social profiles, and websites according to your targets, summarizes with
an LLM (DeepSeek by default), and delivers via Telegram.

Everything runs on your machine. Your data and configurations never leave
except for the API calls you explicitly configure (DeepSeek + Telegram).

Version: 1.0.0 "Berkut-M"
"""
__version__ = "1.0.0"
CODENAME = "Berkut-M"
DISPLAY_VERSION = f'{__version__} "{CODENAME}"'
