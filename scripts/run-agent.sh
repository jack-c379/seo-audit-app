#!/bin/bash

# Navigate to the agent directory
cd "$(dirname "$0")/../agent" || exit 1

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
  echo "ERROR: Virtual environment not found. Please run the setup script first:" >&2
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

# Activate the virtual environment
source .venv/bin/activate

# Run the agent
.venv/bin/python agent.py
