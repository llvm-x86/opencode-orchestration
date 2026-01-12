# AGENTS.md - Developer Guidelines for Agentic Coding

This repository contains a Telegram-based orchestrator for controlling agentic CLI sessions (like `opencode`) within `tmux`. This document provides essential information for AI agents and human developers working on this codebase.

## 0. Purpose and Vision

**Sole Purpose**: To enable stateless development by orchestrating agentic CLI sessions in `tmux` via a Telegram interface.

**Vision**: 
- Spawn multiple agentic CLIs in isolated `tmux` sessions.
- Control any CLI from a central Telegram bot or "tab over" to prompt manually via `tmux attach`.
- Support "Stateless Development": The development environment persists in `tmux`, allowing the bot to be restarted or the user to switch devices without losing state.
- Automate repetitive tasks through dedicated scripts.

## 1. Build, Lint, and Test Commands

The project uses a Python virtual environment and `tmux` for session management.

### Environment Setup
- **Python Version**: 3.13+
- **Virtual Environment**: Located in `./venv/`
- **Dependencies**: Managed via `pip`. Main dependencies: `python-telegram-bot`, `httpx`.
- **Initialization**: `pip install -r requirements.txt`

### Running the Application
To start the Telegram bot, ensure the `TELEGRAM_TOKEN` environment variable is set and execute the runner script:
```bash
./run_bot.sh
```
*(Note: `run_bot.sh` loads variables from `.env` if present.)*

### Linting & Formatting
The project uses `ruff` for both linting and formatting.
- **Check Linting**: `ruff check .`
- **Auto-fix Linting**: `ruff check --fix .`
- **Format Code**: `ruff format .`

### Testing
- **End-to-End Integration Test**: `python3 ab_test_api.py`
  - This script verifies the bridge between the Telegram bot and the agent API.
- **Unit Testing**: Currently, no formal unit testing framework is configured. Use `pytest` for new tests.
  - **Proposed Test Command**: `./venv/bin/pytest`
  - **Run Single Test**: `./venv/bin/pytest tests/test_file.py::test_name`

---

## 2. Code Style Guidelines

All contributions should follow these conventions to maintain consistency.

### General Conventions
- **Language**: Python 3.13+
- **Formatting**: Follow PEP 8. Use `ruff format` for consistent indentation (4 spaces).
- **Naming**:
    - **Functions/Variables**: `snake_case` (e.g., `start_session`, `user_active_session`).
    - **Constants**: `UPPER_SNAKE_CASE` (e.g., `SESSION_NAME`).
    - **Classes**: `PascalCase`.

### Imports
Group imports in the following order:
1. Standard library imports (e.g., `os`, `subprocess`, `logging`).
2. Third-party library imports (e.g., `telegram`, `httpx`).
3. Local application/library imports.

Example:
```python
import os
import subprocess

from telegram import Update
from telegram.ext import ContextTypes
```

### Type Hinting
Always use type hints for function signatures, especially for Telegram handlers.
```python
async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ...
```

### Error Handling
- Use `try...except` blocks when performing system operations like `subprocess.run` or network calls via `httpx`.
- Always verify the existence of `update.effective_message` and `update.effective_user` before attempting to reply or access user data.
- Provide descriptive error messages to the user via Telegram when operations fail.

### Tmux Integration
- Use `run_tmux(cmd)` utility function for all `tmux` interactions.
- Sessions should be managed dynamically using user-provided names.
- Ensure `capture-pane` output is trimmed (Telegram limit is ~4096 chars).

### Logging
- Use the standard `logging` module.
- Log level should be set to `DEBUG` for file logging (`telegram_bot.log`) and `INFO` for console.
- Include timestamps and log levels in the format.

---

## 3. Project Structure

- `telegram_agent.py`: Main entry point containing bot handlers and orchestrator logic.
- `run_bot.sh`: Shell script to activate venv and launch the bot.
- `send_telegram.py`: CLI utility for agents to send messages back to the user.
- `check_messages.py`: CLI utility to fetch new messages from `operator_chat.log`.
- `ab_test_api.py`: Integration test for the API bridge.
- `last_chat_id.txt`: Persists the last active Telegram chat ID.
- `log_pointer.txt`: Tracks the read position in `operator_chat.log`.

---

## 4. Operational Instructions for Agents

When an agentic session starts (e.g., via `opencode serve` or `opencode run`), it must adhere to its role as a **remote developer operator**.

### Mandatory Startup Checklist for Agents
1.  **Read Context**: Immediately read `operator_chat.log` to see the latest user instructions.
2.  **Stateless Loop**:
    *   **Check**: Use `python3 check_messages.py` to identify new user prompts. This script uses `log_pointer.txt` to avoid duplicate processing.
    *   **Act**: Execute the requested coding task.
    *   **Reply**: Once a task is done or if clarification is needed, use `./venv/bin/python send_telegram.py "Your response"` to update the user.
3.  **Tmux Persistence**: Never kill the main `tmux` sessions unless explicitly asked. The user may "tab over" to check your work manually.

### Communication Protocol (CRITICAL)
- **NO TEXT RESPONSES**: You are running in a headless environment. Standard text output is invisible to the user.
- **ALWAYS USE THE TOOL**: For every single interaction, you MUST use the `send_telegram.py` script to send your reply.
- **Example**:
  User: "Hello"
  You: (Runs tool) `./venv/bin/python send_telegram.py "Hello! How can I help?"`

### Workspace & Repositories
- **Clone Location**: Always clone repositories into the `github_work_desk/` directory.
- **Path**: Use absolute paths, e.g., `/root/agent_programmer/github_work_desk/<repo_name>`.
- **Gitignore**: This directory is ignored by git to keep the agent workspace clean.

### Multi-Agent Orchestration
If you are the "main" orchestrator:
- You can spawn sub-agents using `tmux new-session -d -s <name> opencode`.
- Control sub-agents by injecting instructions via `tmux send-keys -t <name> "Your instruction" Enter`.
- Monitor their progress using `tmux capture-pane -pt <name>`.
- You are responsible for aggregating their results and reporting back to the user on Telegram.

---

## 5. Cursor & Copilot Rules

- **Rule 1**: Prefer `subprocess.Popen` for long-running processes (like spawning the agent) to avoid blocking the bot's event loop.
- **Rule 2**: Use `Markdown` or `MarkdownV2` for Telegram messages containing code blocks or terminal output.
- **Rule 3**: When calling the `opencode` API, always verify session existence first and sort by activity if multiple sessions exist.

---
*End of AGENTS.md*
