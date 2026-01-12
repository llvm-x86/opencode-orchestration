import os
import sys
import httpx
import asyncio


async def send_message(text):
    token = os.environ.get("TELEGRAM_TOKEN")

    # Try loading from .env if not found
    if not token and os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("TELEGRAM_TOKEN="):
                    token = line.strip().split("=", 1)[1].strip("'\"")
                    break

    if not token:
        print("TELEGRAM_TOKEN not set")
        return

    chat_id_file = "last_chat_id.txt"
    if not os.path.exists(chat_id_file):
        print("No chat_id found. User must message the bot first.")
        return

    with open(chat_id_file, "r") as f:
        chat_id = f.read().strip()

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, timeout=10.0)
            if resp.status_code == 200:
                print("Sent successfully.")
            else:
                print(f"Failed to send: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"Exception sending message: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_telegram.py 'message'")
    else:
        asyncio.run(send_message(sys.argv[1]))
