# Stateless Agent Orchestrator (Opencode Exclusive)

This repository contains a specialized orchestration layer designed **exclusively for the [Opencode](https://github.com/opencode-ai/opencode) CLI agent**.

It enables a "Stateless Development" workflow where the AI agent operates in a persistent, headless `tmux` environment, while the human operator controls it remotely via a Telegram bot.

## Core Concept: The Stateless Bridge

The system solves the problem of maintaining context and session state when the user switches devices or restarts their local machine.

1.  **The Agent (`opencode`)**: Runs inside a `tmux` session. It is persistent. It has no direct UI; it "speaks" by executing a tool (`send_telegram.py`).
2.  **The Bridge (`telegram_agent.py`)**: A lightweight Python process that:
    *   Polls Telegram for user messages.
    *   **Routes** messages directly into the agent's brain via the `opencode` REST API (`POST /session/:id/prompt_async`).
    *   Does **not** execute code itself. It is a dumb pipe.
3.  **The Loop**:
    *   User sends "Refactor main.py" on Telegram.
    *   Bridge injects prompt into Agent's session via API.
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
```
*Security Note*: Edit `telegram_agent.py` and set `ALLOWED_USER_ID` to the operator's Telegram ID.

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
Use the provided runner script. It handles everything:
```bash
./run_bot.sh
```
This script will:
1.  Source the `.env`.
2.  Start `telegram_agent.py`.
3.  Ensure `opencode serve` (the API) is running or accessible.

### 5. Operation
-   **Workspace**: All coding work should happen in `github_work_desk/` (automatically git-ignored).
-   **Communication**: The agent *must* use `send_telegram.py` to talk to the user. Standard output is invisible.

## Project Structure

-   `telegram_agent.py`: The bridge logic. Manages `tmux` sessions and API forwarding.
-   `AGENTS.md`: The "Constitution" for the sub-agent. It dictates behavior and protocols.
-   `ab_test_api.py`: A self-verification script to ensure the API bridge is working.
-   `send_telegram.py`: The "mouth" of the agent.

## License

MIT
