#!/bin/bash

# Navigate to the project root directory (where .venv should be)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

# Agent directory
AGENT_DIR="$PROJECT_ROOT/agent"

# Check if virtual environment exists in project root
if [ ! -d ".venv" ]; then
  echo "ERROR: Virtual environment not found in project root. Please run the setup script first:" >&2
  echo "  npm run install:agent" >&2
  echo "  or" >&2
  echo "  ./scripts/setup-agent.sh" >&2
  exit 1
fi

# Check Python version in virtual environment
VENV_PYTHON=.venv/bin/python
if [ -f "$VENV_PYTHON" ]; then
  VENV_VERSION=$($VENV_PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
  if [ -n "$VENV_VERSION" ]; then
    VENV_MAJOR=$(echo "$VENV_VERSION" | cut -d. -f1)
    VENV_MINOR=$(echo "$VENV_VERSION" | cut -d. -f2)
    if [ "$VENV_MAJOR" -lt 3 ] || ([ "$VENV_MAJOR" -eq 3 ] && [ "$VENV_MINOR" -lt 10 ]); then
      echo "ERROR: Virtual environment uses Python $VENV_VERSION, but Python 3.10+ is required." >&2
      echo "Please recreate the virtual environment:" >&2
      echo "  rm -rf .venv" >&2
      echo "  npm run install:agent" >&2
      exit 1
    fi
  fi
fi

# Use the virtual environment's Python directly (more reliable than activation)
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

# Verify venv Python exists
if [ ! -f "$VENV_PYTHON" ]; then
  echo "ERROR: Virtual environment Python not found at $VENV_PYTHON" >&2
  exit 1
fi

# Navigate to agent directory and run the agent with venv Python
cd "$AGENT_DIR" || exit 1
"$VENV_PYTHON" agent.py
