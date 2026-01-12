import os
import subprocess
import logging
import httpx
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
    filename="telegram_bot.log",
    filemode="w",
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger("").addHandler(console)

SESSION_NAME = "agent_session"
ALLOWED_USER_ID = 6715827541  # Your ID
user_active_session = {}


def run_tmux(cmd):
    try:
        result = subprocess.run(["tmux"] + cmd, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {str(e)}"


async def start_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user:
        return

    if update.effective_user.id != ALLOWED_USER_ID:
        await update.effective_message.reply_text("⛔ Unauthorized.")
        return

    name = context.args[0] if context.args else "default_agent"
    sessions = run_tmux(["list-sessions"])
    if name in sessions:
        await update.effective_message.reply_text(f"Session '{name}' already exists.")
    else:
        subprocess.Popen(
            ["tmux", "new-session", "-d", "-s", name, "/root/.opencode/bin/opencode"]
        )
        await update.effective_message.reply_text(f"🚀 Spawned agent session: {name}")
    user_active_session[update.effective_user.id] = name
    await update.effective_message.reply_text(f"Switched to: {name}")


async def list_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message:
        return
    sessions = run_tmux(["list-sessions", "-F", "#S"])
    if not sessions:
        await update.effective_message.reply_text("No active agents.")
    else:
        await update.effective_message.reply_text(f"Active Agents:\n{sessions}")


async def switch_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user or not context.args:
        if update.effective_message:
            await update.effective_message.reply_text("Usage: /switch <name>")
        return
    name = context.args[0]
    user_active_session[update.effective_user.id] = name
    await update.effective_message.reply_text(f"Now controlling: {name}")


async def screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user:
        return
    session = user_active_session.get(update.effective_user.id, "default_agent")
    content = run_tmux(["capture-pane", "-pt", session])
    if "can't find session" in content.lower():
        await update.effective_message.reply_text(f"Session '{session}' not found.")
    else:
        if len(content) > 3500:
            content = "..." + content[-3500:]
        await update.effective_message.reply_text(
            f"State [{session}]:\n```\n{content}\n```", parse_mode="Markdown"
        )


async def stop_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user:
        return
    session = (
        context.args[0]
        if context.args
        else user_active_session.get(update.effective_user.id)
    )
    if not session:
        await update.effective_message.reply_text(
            "Specify session name or switch to one first."
        )
        return
    run_tmux(["kill-session", "-t", session])
    await update.effective_message.reply_text(f"🛑 Killed session: {session}")


def send_to_tmux_session(session_name: str, text: str) -> bool:
    """Sends text to a tmux session using send-keys."""
    try:
        # Escape double quotes in the text for shell safety
        escaped_text = text.replace('"', '\\"')
        result = subprocess.run(
            ["tmux", "send-keys", "-t", session_name, escaped_text, "Enter"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            logging.info(f"Sent to tmux session '{session_name}': {text[:50]}...")
            return True
        else:
            logging.error(f"tmux send-keys failed: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"tmux send-keys exception: {e}")
        return False


async def forward_to_agent(text: str, tmux_session: str = "default_agent") -> bool:
    """Forwards the message to an agent via tmux send-keys (primary) or API (fallback)."""
    logging.debug(f"Attempting to forward text: {text}")

    # Primary method: Use tmux send-keys to inject directly into the agent session
    sessions_output = subprocess.run(
        ["tmux", "list-sessions", "-F", "#S"], capture_output=True, text=True
    )
    active_tmux_sessions = sessions_output.stdout.strip().split("\n")

    # Append system instruction to ensure the agent uses the response tool
    system_instruction = " (IMPORTANT: Do not print your response. You MUST use the tool: ./venv/bin/python send_telegram.py 'your response')"
    full_text = text + system_instruction

    if tmux_session in active_tmux_sessions:
        if send_to_tmux_session(tmux_session, full_text):
            return True
        logging.warning(f"tmux send-keys failed, falling back to API...")

    # Fallback: Use the opencode REST API
    async with httpx.AsyncClient() as client:
        try:
            sessions_resp = await client.get("http://localhost:4096/session")
            if sessions_resp.status_code != 200:
                logging.error(f"Failed to fetch sessions: {sessions_resp.status_code}")
                return False

            sessions = sessions_resp.json()
            if not sessions:
                logging.error("No active sessions found in API response")
                return False

            session_id = sessions[0]["id"]
            logging.debug(f"Forwarding to session_id: {session_id}")

            response = await client.post(
                f"http://localhost:4096/session/{session_id}/prompt_async",
                json={"parts": [{"type": "text", "text": text}]},
            )
            logging.debug(f"API Response: {response.status_code} - {response.text}")
            return response.status_code in (200, 204)
        except Exception as e:
            logging.error(f"API Forward Exception: {e}")
            return False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if (
        not update.effective_message
        or not update.effective_message.text
        or not update.effective_user
        or not update.effective_chat
    ):
        return

    user_id = update.effective_user.id
    if user_id != ALLOWED_USER_ID:
        logging.warning(f"Unauthorized access attempt from user ID: {user_id}")
        await update.effective_message.reply_text("⛔ Unauthorized access.")
        return

    text = update.effective_message.text
    chat_id = str(update.effective_chat.id)

    logging.info(f"Received message from {chat_id}: {text}")

    with open("last_chat_id.txt", "w") as f:
        f.write(chat_id)

    with open("operator_chat.log", "a") as f:
        f.write(f"USER: {text}\n")

    # Get the user's active tmux session or default to "default_agent"
    tmux_session = user_active_session.get(user_id, "default_agent")
    success = await forward_to_agent(text, tmux_session)

    if success:
        await update.effective_message.reply_text("Instruction queued to agent.")
    else:
        await update.effective_message.reply_text(
            "❌ Failed to queue instruction. Check logs."
        )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message:
        return
    text = (
        "/start <name> - Spawn/attach to agent\n"
        "/list - List all agents\n"
        "/switch <name> - Switch active control\n"
        "/screen - View agent state\n"
        "/stop <name> - Kill an agent\n"
        "Just type to send keys to the active agent."
    )
    await update.effective_message.reply_text(text)


if __name__ == "__main__":
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("Set TELEGRAM_TOKEN")
        exit(1)

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_session))
    app.add_handler(CommandHandler("list", list_sessions))
    app.add_handler(CommandHandler("switch", switch_session))
    app.add_handler(CommandHandler("screen", screen))
    app.add_handler(CommandHandler("stop", stop_session))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Orchestrator Online...")
    app.run_polling()
