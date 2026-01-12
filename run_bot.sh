#!/bin/bash
# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "Error: TELEGRAM_TOKEN is not set."
    echo "Please set it in .env or as an environment variable."
    exit 1
fi

./venv/bin/python telegram_agent.py
