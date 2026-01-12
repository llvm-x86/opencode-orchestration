# Stateless Agent Orchestrator

This project provides a Telegram-based interface for orchestrating "stateless" agentic coding sessions. It uses `tmux` to maintain persistent CLI sessions for agents (like `opencode`) while allowing the operator (you) to control them via a simple Telegram bot.

## Features

-   **Stateless Control**: The Python bot acts as a bridge. Restarting the bot or switching devices does not kill the underlying agent sessions.
-   **Telegram Interface**: Control your agents from anywhere using Telegram.
-   **API Integration**: Messages are routed directly to the `opencode` agent's REST API for immediate processing.
-   **Multi-Agent Support**: Spawn and switch between multiple named agent sessions.
-   **Security**: Restricted access to a specific Telegram User ID.

## Prerequisites

-   Python 3.13+
-   `tmux`
-   `opencode` CLI tool installed and available in the path.
-   A Telegram Bot Token (from @BotFather).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Set up the environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configure environment variables:**
    Create a `.env` file in the root directory:
    ```bash
    TELEGRAM_TOKEN=your_telegram_bot_token_here
    ```

    *Note: You must also configure the `ALLOWED_USER_ID` in `telegram_agent.py` to match your Telegram ID for security.*

## Usage

1.  **Start the Orchestrator:**
    ```bash
    ./run_bot.sh
    ```
    This script will:
    -   Activate the virtual environment.
    -   Start the Telegram bot.
    -   Ensure the `opencode` API server is reachable (started by the bot if needed, or assumed running).

2.  **Talk to your Agent:**
    Open your bot in Telegram and send a message.
    -   **Direct Messages**: Any text sent is forwarded to the active sub-agent session.
    -   **Commands**:
        -   `/start <name>`: Spawn or switch to a session named `<name>`.
        -   `/list`: List active sessions.
        -   `/screen`: View the current `tmux` pane content (screenshot).
        -   `/stop <name>`: Kill a specific session.

## Architecture

-   **`telegram_agent.py`**: The main bot logic. It polls Telegram for updates and forwards prompts to the local `opencode` API.
-   **`opencode serve`**: Runs in the background (or in a tmux session) to provide the REST API that the bot talks to.
-   **`tmux`**: Hosts the actual agent CLI sessions (`opencode run`), keeping them alive independently of the bot process.
-   **`AGENTS.md`**: Instructions for the AI agents operating within this environment.

## Development

-   **Logs**: Check `telegram_bot.log` for debugging bot issues.
-   **Work Desk**: Agents are instructed to clone work repositories into `github_work_desk/`.

## License

[License Name]
