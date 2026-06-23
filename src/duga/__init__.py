"""Duga - Personal daily briefing agent.

A lightweight, fully local AI agent that gathers information from the web,
social profiles, and websites according to your targets, summarizes with
an LLM (DeepSeek by default), and delivers via Telegram.

Everything runs on your machine. Your data and configurations never leave
except for the API calls you explicitly configure (DeepSeek + Telegram).

Version: 0.2.0 "Berkut-B"
"""
__version__ = "0.2.0"
CODENAME = "Berkut-B"
DISPLAY_VERSION = f'{__version__} "{CODENAME}"'
