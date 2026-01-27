import os
import sys
import httpx
import asyncio


async def send_document(file_path, caption=None):
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

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    
    async with httpx.AsyncClient() as client:
        try:
            with open(file_path, "rb") as f:
                files = {"document": (os.path.basename(file_path), f)}
                data = {"chat_id": chat_id}
                if caption:
                    data["caption"] = caption
                    
                resp = await client.post(url, data=data, files=files, timeout=30.0)
                
                if resp.status_code == 200:
                    print(f"File '{file_path}' sent successfully.")
                else:
                    print(f"Failed to send file: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"Exception sending file: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_file_telegram.py <file_path> [caption]")
    else:
        path = sys.argv[1]
        cap = sys.argv[2] if len(sys.argv) > 2 else None
        asyncio.run(send_document(path, cap))
