# Telegram Bot (Python) — Long Polling — Railway Deploy

A minimal Telegram bot using `python-telegram-bot` (v20+) with **long polling**, ready to deploy on **Railway** as a worker.

## Quick Start (Local)
1. **Create and activate venv**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
2. **Install deps**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set your token and run**
   ```bash
   export TELEGRAM_TOKEN="123456:ABCDEF..."   # Windows (PowerShell): $env:TELEGRAM_TOKEN="..."
   python main.py
   ```
   You should see logs like `Starting bot with long polling...`. Send `/start` to your bot on Telegram.

## Deploy to Railway (24/7)
1. Push this folder to a **new GitHub repo**.
2. Go to Railway → **New Project** → **Deploy from GitHub** → select your repo.
3. After first build, open your service → **Variables** → add `TELEGRAM_TOKEN` with your BotFather token.
4. Railway detects the `Procfile` and runs it as a **worker**. Watch logs → you should see `Starting bot with long polling...`.

## What Long Polling Is (super short)
The bot keeps requesting Telegram for updates (`getUpdates`) with a long timeout. When messages arrive, Telegram replies; the bot processes them and immediately asks again. No public URL or SSL needed.

## Files
- `main.py` — bot code (async, long polling)
- `requirements.txt` — Python deps
- `Procfile` — tells Railway to run `python -u main.py` as a worker
- `.env.example` — sample env file (local usage)
- `.gitignore` — ignores venv, caches, .env

## Add Your Features
- Add more commands with new `CommandHandler`s.
- Add inline keyboards, callbacks, etc. using `python-telegram-bot` docs.