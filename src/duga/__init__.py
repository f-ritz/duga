"""Duga - Personal daily briefing agent.

A lightweight, fully local AI agent that gathers information from the web,
social profiles, and websites according to your targets, summarizes with
an LLM (DeepSeek by default), and delivers via Telegram.

Everything runs on your machine. Your data and configurations never leave
except for the API calls you explicitly configure (DeepSeek + Telegram).

Version: 1.1.1 'Berkut-AM'
"""
__version__ = "1.1.1"
CODENAME = "Berkut-AM"
DISPLAY_VERSION = f'{__version__} "{CODENAME}"'
