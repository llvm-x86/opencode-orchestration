import os
import sys
import asyncio
from telegram import Bot


async def send_message(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    # We need a way to know the chat_id.
    # For a personal bot, we can store the last chat_id in a file.
    if not token:
        print("TELEGRAM_TOKEN not set")
        return

    chat_id_file = "last_chat_id.txt"
    if not os.path.exists(chat_id_file):
        print("No chat_id found. User must message the bot first.")
        return

    with open(chat_id_file, "r") as f:
        chat_id = f.read().strip()

    bot = Bot(token)
    async with bot:
        await bot.send_message(chat_id=chat_id, text=text)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_telegram.py 'message'")
    else:
        asyncio.run(send_message(sys.argv[1]))
