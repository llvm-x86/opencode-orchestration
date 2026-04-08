import os
import subprocess
import logging
import httpx
import time
import json
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
DEFAULT_MODEL = os.environ.get("OPENCODE_MODEL", "openai/gpt-5.4")
DEFAULT_VARIANT = os.environ.get("OPENCODE_VARIANT", "low")
DEFAULT_YOLO = os.environ.get("OPENCODE_YOLO", "").lower() in {"1", "true", "yes", "on"}
user_active_session = {}
YOLO_PERMISSION_CONFIG = {"*": "allow"}


def run_tmux(cmd):
    try:
        result = subprocess.run(["tmux"] + cmd, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {str(e)}"


def opencode_command(
    continue_last: bool = False, session_id: str | None = None, fork: bool = False
) -> list[str]:
    command = ["/root/.opencode/bin/opencode"]
    if session_id:
        command.extend(["--session", session_id])
    elif continue_last:
        command.append("--continue")
    if fork and (continue_last or session_id):
        command.append("--fork")
    return command


def opencode_environment(yolo: bool = False) -> dict[str, str]:
    env = os.environ.copy()
    config: dict[str, object] = {}
    existing = env.get("OPENCODE_CONFIG_CONTENT")
    if existing:
        try:
            parsed = json.loads(existing)
            if isinstance(parsed, dict):
                config.update(parsed)
        except json.JSONDecodeError:
            logging.warning("Ignoring invalid OPENCODE_CONFIG_CONTENT while enabling yolo mode.")

    agent_config = config.get("agent")
    if not isinstance(agent_config, dict):
        agent_config = {}
        config["agent"] = agent_config

    build_config = agent_config.get("build")
    if not isinstance(build_config, dict):
        build_config = {}
        agent_config["build"] = build_config

    build_config["model"] = DEFAULT_MODEL
    if DEFAULT_VARIANT:
        build_config["variant"] = DEFAULT_VARIANT

    if not yolo:
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)
        return env

    config["permission"] = dict(YOLO_PERMISSION_CONFIG)
    env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)
    return env


def list_opencode_sessions() -> str:
    try:
        result = subprocess.run(
            ["/root/.opencode/bin/opencode", "session", "list"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to list opencode sessions: {e.stderr}")
        return ""


def spawn_agent_session(
    name: str,
    continue_last: bool = False,
    opencode_session_id: str | None = None,
    fork: bool = False,
    yolo: bool = False,
) -> None:
    subprocess.Popen(
        [
            "tmux",
            "new-session",
            "-d",
            "-s",
            name,
            *opencode_command(
                continue_last=continue_last,
                session_id=opencode_session_id,
                fork=fork,
            ),
        ],
        env=opencode_environment(yolo=yolo),
    )


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
        spawn_agent_session(name, yolo=DEFAULT_YOLO)
        await update.effective_message.reply_text(f"🚀 Spawned agent session: {name}")
    user_active_session[update.effective_user.id] = name
    await update.effective_message.reply_text(f"Switched to: {name}")


async def start_session_yolo(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        spawn_agent_session(name, yolo=True)
        await update.effective_message.reply_text(
            f"🚀 Spawned yolo agent session: {name}"
        )
    user_active_session[update.effective_user.id] = name
    await update.effective_message.reply_text(f"Switched to: {name}")


async def session_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user:
        return
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.effective_message.reply_text("⛔ Unauthorized.")
        return

    sessions = list_opencode_sessions()
    if not sessions:
        await update.effective_message.reply_text("No resumable opencode sessions found.")
        return

    if len(sessions) > 3500:
        sessions = sessions[:3500] + "\n..."
    await update.effective_message.reply_text(
        f"Opencode Sessions:\n```\n{sessions}\n```", parse_mode="Markdown"
    )


async def resume_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user:
        return
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.effective_message.reply_text("⛔ Unauthorized.")
        return

    if not context.args:
        await update.effective_message.reply_text(
            "Usage: /resume <opencode_session_id> [tmux_name]\n"
            "Use /history to see resumable session IDs."
        )
        return

    opencode_session_id = context.args[0]
    tmux_name = context.args[1] if len(context.args) > 1 else "default_agent"
    sessions = run_tmux(["list-sessions", "-F", "#S"])
    if tmux_name in sessions.splitlines():
        await update.effective_message.reply_text(
            f"Session '{tmux_name}' already exists. Use /switch {tmux_name} or /stop {tmux_name} first."
        )
        return

    spawn_agent_session(
        tmux_name,
        opencode_session_id=opencode_session_id,
        yolo=DEFAULT_YOLO,
    )
    user_active_session[update.effective_user.id] = tmux_name
    await update.effective_message.reply_text(
        f"🔄 Resumed opencode session `{opencode_session_id}` in tmux session `{tmux_name}`.",
        parse_mode="Markdown",
    )


async def resume_last_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user:
        return
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.effective_message.reply_text("⛔ Unauthorized.")
        return

    tmux_name = context.args[0] if context.args else "default_agent"
    sessions = run_tmux(["list-sessions", "-F", "#S"])
    if tmux_name in sessions.splitlines():
        await update.effective_message.reply_text(
            f"Session '{tmux_name}' already exists. Use /switch {tmux_name} or /stop {tmux_name} first."
        )
        return

    spawn_agent_session(tmux_name, continue_last=True, yolo=DEFAULT_YOLO)
    user_active_session[update.effective_user.id] = tmux_name
    await update.effective_message.reply_text(
        f"🔄 Resumed the latest opencode chat in tmux session `{tmux_name}`.",
        parse_mode="Markdown",
    )


async def resume_session_yolo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user:
        return
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.effective_message.reply_text("⛔ Unauthorized.")
        return

    if not context.args:
        await update.effective_message.reply_text(
            "Usage: /resume_yolo <opencode_session_id> [tmux_name]\n"
            "Use /history to see resumable session IDs."
        )
        return

    opencode_session_id = context.args[0]
    tmux_name = context.args[1] if len(context.args) > 1 else "default_agent"
    sessions = run_tmux(["list-sessions", "-F", "#S"])
    if tmux_name in sessions.splitlines():
        await update.effective_message.reply_text(
            f"Session '{tmux_name}' already exists. Use /switch {tmux_name} or /stop {tmux_name} first."
        )
        return

    spawn_agent_session(tmux_name, opencode_session_id=opencode_session_id, yolo=True)
    user_active_session[update.effective_user.id] = tmux_name
    await update.effective_message.reply_text(
        f"🔄 Resumed opencode session `{opencode_session_id}` in yolo mode as tmux session `{tmux_name}`.",
        parse_mode="Markdown",
    )


async def resume_last_session_yolo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user:
        return
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.effective_message.reply_text("⛔ Unauthorized.")
        return

    tmux_name = context.args[0] if context.args else "default_agent"
    sessions = run_tmux(["list-sessions", "-F", "#S"])
    if tmux_name in sessions.splitlines():
        await update.effective_message.reply_text(
            f"Session '{tmux_name}' already exists. Use /switch {tmux_name} or /stop {tmux_name} first."
        )
        return

    spawn_agent_session(tmux_name, continue_last=True, yolo=True)
    user_active_session[update.effective_user.id] = tmux_name
    await update.effective_message.reply_text(
        f"🔄 Resumed the latest opencode chat in yolo mode as tmux session `{tmux_name}`.",
        parse_mode="Markdown",
    )


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


async def send_key(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    if not update.effective_message or not update.effective_user:
        return
    session = user_active_session.get(update.effective_user.id, "default_agent")
    ensure_session(session)
    result = run_tmux(["send-keys", "-t", session, key])
    if "Error" in result:
        await update.effective_message.reply_text(f"❌ Failed to send {key}: {result}")
    else:
        await update.effective_message.reply_text(f"⌨️ Sent {key} to {session}")


async def enter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_key(update, context, "Enter")


async def up_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_key(update, context, "Up")


async def down_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_key(update, context, "Down")


async def left_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_key(update, context, "Left")


async def right_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_key(update, context, "Right")


async def esc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_key(update, context, "Escape")


async def compact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user:
        return
    session = user_active_session.get(update.effective_user.id, "default_agent")
    ensure_session(session)
    if send_to_tmux_session(session, "/compact"):
        await update.effective_message.reply_text(f"🗜️ Sent /compact to {session}")
    else:
        await update.effective_message.reply_text(f"❌ Failed to send /compact to {session}")


async def get_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user:
        return
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.effective_message.reply_text("⛔ Unauthorized.")
        return
    if not context.args:
        await update.effective_message.reply_text("Usage: /get <path>")
        return

    path = context.args[0]
    # If relative, look in github_work_desk
    if not os.path.isabs(path):
        path = os.path.join("github_work_desk", path)

    abs_path = os.path.abspath(path)

    if not os.path.exists(abs_path):
        await update.effective_message.reply_text(
            f"❌ File not found: `{abs_path}`", parse_mode="Markdown"
        )
        return

    if os.path.isdir(abs_path):
        await update.effective_message.reply_text(
            f"📁 `{abs_path}` is a directory. Please specify a file.",
            parse_mode="Markdown",
        )
        return

    try:
        with open(abs_path, "rb") as f:
            await update.effective_message.reply_document(
                document=f, filename=os.path.basename(abs_path)
            )
    except Exception as e:
        logging.error(f"Error sending file: {e}")
        await update.effective_message.reply_text(f"❌ Error: {str(e)}")


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user:
        return

    user_id = update.effective_user.id
    if user_id != ALLOWED_USER_ID:
        logging.warning(f"Unauthorized file upload attempt from user ID: {user_id}")
        await update.effective_message.reply_text("⛔ Unauthorized.")
        return

    # Determine file info
    if update.message.document:
        doc = update.message.document
        file_name = doc.file_name or f"file_{update.message.message_id}"
        file_id = doc.file_id
    elif update.message.photo:
        doc = update.message.photo[-1]  # Highest resolution
        file_name = f"photo_{update.message.message_id}.jpg"
        file_id = doc.file_id
    else:
        await update.effective_message.reply_text("❓ Unsupported file type.")
        return

    try:
        file = await context.bot.get_file(file_id)
        os.makedirs("github_work_desk", exist_ok=True)
        dest_path = os.path.abspath(os.path.join("github_work_desk", file_name))

        await file.download_to_drive(dest_path)

        logging.info(f"File saved: {dest_path}")
        await update.effective_message.reply_text(
            f"📥 File saved to: `{dest_path}`", parse_mode="Markdown"
        )

        # Notify the agent
        tmux_session = user_active_session.get(user_id, "default_agent")
        forward_msg = f"System: A new file has been uploaded to {dest_path}"
        await forward_to_agent(forward_msg, tmux_session)

    except Exception as e:
        logging.error(f"Error handling file: {e}")
        await update.effective_message.reply_text(f"❌ Error saving file: {str(e)}")


def send_to_tmux_session(session_name: str, text: str) -> bool:
    """Sends text to a tmux session using send-keys."""
    try:
        # Escape double quotes and backslashes for shell safety
        escaped_text = text.replace("\\", "\\\\").replace('"', '\\"')

        # Send text first
        cmd_text = ["tmux", "send-keys", "-t", session_name, escaped_text]
        logging.info(f"Running command: {' '.join(cmd_text)}")
        subprocess.run(cmd_text, check=True)

        # Small delay to ensure text is processed by TUI
        time.sleep(0.5)

        # Send Enter
        cmd_enter = ["tmux", "send-keys", "-t", session_name, "Enter"]
        logging.info(f"Running command: {' '.join(cmd_enter)}")
        result = subprocess.run(
            cmd_enter,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logging.info(f"Sent to tmux session '{session_name}': {text[:50]}...")
            return True
        else:
            logging.error(
                f"tmux send-keys failed (code {result.returncode}): {result.stderr}"
            )
            return False
    except Exception as e:
        logging.error(f"tmux send-keys exception: {e}")
        return False


async def forward_to_agent(text: str, tmux_session: str = "default_agent") -> bool:
    """Forwards the message to an agent via tmux send-keys (primary) or API (fallback)."""
    logging.debug(f"Attempting to forward text: {text}")

    # Ensure the session exists before trying to forward
    ensure_session(tmux_session)

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
        "/start_yolo [name] - Spawn an agent in approve-all/yolo mode\n"
        "/history - List resumable opencode chats\n"
        "/resume <opencode_session_id> [name] - Resume a specific opencode chat\n"
        "/resume_yolo <opencode_session_id> [name] - Resume a specific chat in yolo mode\n"
        "/resume_last [name] - Resume the most recent opencode chat\n"
        "/resume_last_yolo [name] - Resume the latest chat in yolo mode\n"
        "/list - List all agents\n"
        "/switch <name> - Switch active control\n"
        "/screen - View agent state\n"
        "/stop <name> - Kill an agent\n"
        "/enter - Send Enter key\n"
        "/up, /down, /left, /right - Send arrow keys\n"
        "/esc - Send Escape key\n"
        "/compact - Run the native opencode /compact command\n"
        "/get <path> - Download a file\n"
        "Just type to send keys to the active agent.\n"
        "Send a file or photo to save it to the workspace."
    )
    await update.effective_message.reply_text(text)


def ensure_session(name: str = "default_agent"):
    """Ensures a tmux session with the given name is running."""
    sessions = run_tmux(["list-sessions"])
    if name not in sessions:
        logging.info(f"Auto-spawning session: {name}")
        spawn_agent_session(name, yolo=DEFAULT_YOLO)
        time.sleep(5)  # Wait for agent to boot
        return True
    return False


if __name__ == "__main__":
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("Set TELEGRAM_TOKEN")
        exit(1)

    # Ensure the default agent is running on startup
    ensure_session("default_agent")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_session))
    app.add_handler(CommandHandler("start_yolo", start_session_yolo))
    app.add_handler(CommandHandler("history", session_history))
    app.add_handler(CommandHandler("resume", resume_session))
    app.add_handler(CommandHandler("resume_yolo", resume_session_yolo))
    app.add_handler(CommandHandler("resume_last", resume_last_session))
    app.add_handler(CommandHandler("resume_last_yolo", resume_last_session_yolo))
    app.add_handler(CommandHandler("list", list_sessions))
    app.add_handler(CommandHandler("switch", switch_session))
    app.add_handler(CommandHandler("screen", screen))
    app.add_handler(CommandHandler("stop", stop_session))
    app.add_handler(CommandHandler("get", get_cmd))
    app.add_handler(CommandHandler("enter", enter_cmd))
    app.add_handler(CommandHandler("up", up_cmd))
    app.add_handler(CommandHandler("down", down_cmd))
    app.add_handler(CommandHandler("left", left_cmd))
    app.add_handler(CommandHandler("right", right_cmd))
    app.add_handler(CommandHandler("esc", esc_cmd))
    app.add_handler(CommandHandler("compact", compact_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Orchestrator Online...")
    app.run_polling()
