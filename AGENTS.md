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
- **Dependencies**: Managed via `pip`. Main dependency is `python-telegram-bot`.

### Running the Application
To start the Telegram bot, ensure the `TELEGRAM_TOKEN` environment variable is set and execute the runner script:
```bash
export TELEGRAM_TOKEN='your_token_here'
./run_bot.sh
```

### Linting
The project uses `ruff` for linting and formatting.
- **Check Linting**: `ruff check .`
- **Auto-fix Linting**: `ruff check --fix .`
- **Format Code**: `ruff format .`

### Testing
*Note: Currently, no formal testing framework is configured. It is highly recommended to add `pytest` for unit testing handlers.*
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
2. Third-party library imports (e.g., `telegram`).
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
- Use `try...except` blocks when performing system operations like `subprocess.run`.
- Always verify the existence of `update.effective_message` before attempting to reply.
- Provide descriptive error messages to the user via Telegram.

### Tmux Integration
- Use `run_tmux(cmd)` utility function for all `tmux` interactions.
- Sessions should be managed dynamically using user-provided names.
- Ensure `capture-pane` output is trimmed (Telegram limit is ~4096 chars).

### Logging
- Use the standard `logging` module.
- Log level should be set to `INFO` by default.
- Include timestamps and log levels in the format.

---

## 3. Project Structure

- `telegram_agent.py`: Main entry point containing bot handlers and orchestrator logic.
- `run_bot.sh`: Shell script to activate venv and launch the bot.
- `venv/`: Local Python virtual environment.

---

## 4. Operational Instructions for Agents

When an agentic session starts (e.g., via `opencode serve` or `opencode run`), it must adhere to its role as a **remote developer operator**.

### Mandatory Startup Checklist for Agents
1.  **Read Context**: Immediately read `operator_chat.log` to see the latest user instructions.
2.  **Stateless Loop**:
    *   **Check**: Use `python3 check_messages.py` to identify new user prompts since the last action.
    *   **Act**: Execute the requested coding task (fixing bugs, building features, etc.).
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
- Monitor their progress using `tmux capture-pane -pt <name>`.
- You are responsible for aggregating their results and reporting back to the user on Telegram.

---

---

## 5. Cursor & Copilot Rules

*No specific `.cursorrules` or `.github/copilot-instructions.md` were found. If added, they should be integrated here.*

- **Rule 1**: Prefer `subprocess.Popen` for long-running processes (like spawning the agent) to avoid blocking the bot's event loop.
- **Rule 2**: Use `Markdown` or `MarkdownV2` for Telegram messages containing code blocks or terminal output.

---
*End of AGENTS.md*
