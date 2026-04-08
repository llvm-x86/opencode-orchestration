# Stateless Agent Orchestrator (Opencode Exclusive)

This repository contains a specialized orchestration layer designed **exclusively for the [Opencode](https://github.com/opencode-ai/opencode) CLI agent**.

It enables a "Stateless Development" workflow where the AI agent operates in a persistent, headless `tmux` environment, while the human operator controls it remotely via a Telegram bot.

## Core Concept: The Stateless Bridge

The system solves the problem of maintaining context and session state when the user switches devices or restarts their local machine.

1.  **The Agent (`opencode`)**: Runs inside a `tmux` session. It is persistent. It has no direct UI; it "speaks" by executing a tool (`send_telegram.py`).
2.  **The Bridge (`telegram_agent.py`)**: A lightweight Python process that:
    *   Polls Telegram for user messages.
    *   **Routes** messages directly into the agent's brain via `tmux send-keys` (primary) or the `opencode` REST API (fallback).
    *   Does **not** execute code itself. It is a dumb pipe.
3.  **The Loop**:
    *   User sends "Refactor main.py" on Telegram.
    *   Bridge injects prompt into Agent's session.
    *   Agent wakes up, reads prompt, edits files, runs tests.
    *   Agent runs `send_telegram.py "Done. Tests passed."` to reply.

## 🚀 Setup Instructions (For Agents)

If you are an AI agent instructed to set this up, follow these steps exactly to replicate the environment:

### 1. Prerequisites
-   **Opencode CLI**: Must be installed and accessible.
-   **Tmux**: Must be installed.
-   **Python 3.13+**: Required for the bridge script.

### 2. Environment Configuration
Create a `.env` file in the root:
```bash
TELEGRAM_TOKEN=your_token_here
OPENCODE_MODEL=openai/gpt-5.4
OPENCODE_VARIANT=low
OPENCODE_YOLO=false
```
*Security Note*: Edit `telegram_agent.py` and set `ALLOWED_USER_ID` to the operator's Telegram ID.

If `OPENCODE_MODEL` is omitted, the orchestrator defaults to `openai/gpt-5.4`.
If `OPENCODE_VARIANT` is omitted, the orchestrator defaults to `low`.
If `OPENCODE_YOLO=true`, newly auto-spawned sessions default to approve-all mode.

### 3. Installation
```bash
# Clone this repo (if not already present)
# git clone git@github.com:llvm-x86/opencode-orchestration.git

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Launching the Orchestrator

#### Option A: Quick Start (Tmux)
To keep the bot running after you close your terminal, run it inside a tmux session:
```bash
tmux new-session -s orchestrator
./run_bot.sh
# Press Ctrl+B, then D to detach
```

#### Option B: Production (Systemd)
To make the bot run indefinitely, start on boot, and restart on crash:

1.  Edit `opencode-orchestrator.service` and verify the paths (`WorkingDirectory`, `User`, `ExecStart`).
2.  Install the service:
    ```bash
    sudo cp opencode-orchestrator.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable opencode-orchestrator
    sudo systemctl start opencode-orchestrator
    ```
3.  Check status:
    ```bash
    sudo systemctl status opencode-orchestrator
    ```

### 5. Operation
-   **Workspace**: All coding work should happen in `github_work_desk/` (automatically git-ignored).
-   **Communication**: The agent *must* use `send_telegram.py` to talk to the user. Standard output is invisible.
-   **Resuming chats**: Use `/history` to list prior `opencode` session IDs, `/resume <session_id> [tmux_name]` to reopen a specific chat, or `/resume_last [tmux_name]` to continue the most recent chat in a new tmux session.
-   **Approve-all mode**: Use `/start_yolo`, `/resume_yolo <session_id> [tmux_name]`, or `/resume_last_yolo [tmux_name]` to launch `opencode` with `permission: allow` (approve-all / yolo mode).

## Project Structure

-   `telegram_agent.py`: The bridge logic. Manages `tmux` sessions and API forwarding.
-   `AGENTS.md`: The "Constitution" for the sub-agent. It dictates behavior and protocols.
-   `ab_test_api.py`: A self-verification script to ensure the API bridge is working.
-   `send_telegram.py`: The "mouth" of the agent.

## License

MIT
