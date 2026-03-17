# Rotterdam Naturalization Appointment Checker

A Python script that checks the Gemeente Rotterdam booking page every 5 minutes and sends you a Telegram message the moment a naturalization appointment becomes available. Runs between 07:01 and 22:00.

## Setup

1. Install dependencies: `pip install selenium beautifulsoup4 requests`
2. Create a Telegram bot via @BotFather and get your bot token
3. Fill in your `BOT_TOKEN` and `CHAT_ID` in the script
4. Run it: `python3 rtm_afspraak.py`

## Don't want to deal with the setup?

Use the hosted version at [010afspraak.nl](https://010afspraak.nl) — pay once, get notified automatically via Telegram. No setup needed.
