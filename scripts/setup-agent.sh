#!/bin/bash

# Navigate to the project root directory (where .venv should be)
PROJECT_ROOT="$(dirname "$0")/.."
cd "$PROJECT_ROOT" || exit 1

# Agent directory
AGENT_DIR="$PROJECT_ROOT/agent"

# Function to check Python version (must be 3.10+)
check_python_version() {
  local python_cmd=$1
  if command -v "$python_cmd" >/dev/null 2>&1; then
    local version=$($python_cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
    if [ -n "$version" ]; then
      local major=$(echo "$version" | cut -d. -f1)
      local minor=$(echo "$version" | cut -d. -f2)
      if [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; then
        echo "$python_cmd"
        return 0
      fi
    fi
  fi
  return 1
}

# Try to find Python 3.10+ (check common locations)
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3; do
  if check_python_version "$cmd"; then
    PYTHON_CMD="$cmd"
    break
  fi
done

# If not found, try checking in common paths
if [ -z "$PYTHON_CMD" ]; then
  # Check Homebrew Python
  if [ -f "/opt/homebrew/bin/python3.12" ]; then
    PYTHON_CMD="/opt/homebrew/bin/python3.12"
  elif [ -f "/opt/homebrew/bin/python3.11" ]; then
    PYTHON_CMD="/opt/homebrew/bin/python3.11"
  elif [ -f "/opt/homebrew/bin/python3.10" ]; then
    PYTHON_CMD="/opt/homebrew/bin/python3.10"
  elif [ -f "/opt/homebrew/bin/python3" ] && check_python_version "/opt/homebrew/bin/python3"; then
    PYTHON_CMD="/opt/homebrew/bin/python3"
  fi
fi

# If still not found, check /usr/local/bin (Intel Mac Homebrew)
if [ -z "$PYTHON_CMD" ]; then
  for cmd in /usr/local/bin/python3.12 /usr/local/bin/python3.11 /usr/local/bin/python3.10 /usr/local/bin/python3; do
    if [ -f "$cmd" ] && check_python_version "$cmd"; then
      PYTHON_CMD="$cmd"
      break
    fi
  done
fi

# Error if no suitable Python found
if [ -z "$PYTHON_CMD" ]; then
  echo "ERROR: Python 3.10 or higher is required but not found." >&2
  echo "" >&2
  echo "Please install Python 3.10+ using one of the following methods:" >&2
  echo "  1. Homebrew: brew install python@3.12" >&2
  echo "  2. Visit: https://www.python.org/downloads/" >&2
  echo "" >&2
  echo "After installing, run this script again." >&2
  exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "Using $PYTHON_CMD ($PYTHON_VERSION)"

# Check if existing virtual environment uses old Python version
if [ -d ".venv" ]; then
  VENV_PYTHON=.venv/bin/python
  if [ -f "$VENV_PYTHON" ]; then
    VENV_VERSION=$($VENV_PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
    if [ -n "$VENV_VERSION" ]; then
      VENV_MAJOR=$(echo "$VENV_VERSION" | cut -d. -f1)
      VENV_MINOR=$(echo "$VENV_VERSION" | cut -d. -f2)
      if [ "$VENV_MAJOR" -lt 3 ] || ([ "$VENV_MAJOR" -eq 3 ] && [ "$VENV_MINOR" -lt 10 ]); then
        echo "Warning: Existing virtual environment uses Python $VENV_VERSION (requires 3.10+)" >&2
        echo "Removing old virtual environment..." >&2
        rm -rf .venv
      fi
    fi
  fi
fi

# Create virtual environment in project root if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment in project root with $PYTHON_CMD..."
  "$PYTHON_CMD" -m venv .venv || exit 1
fi

# Activate the virtual environment
source .venv/bin/activate

# Install requirements using pip from agent directory
pip install -r "$AGENT_DIR/requirements.txt"
