#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "🚀 Starting Auto Archiver macOS installation..."

# --- Check for uv ---
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed."
    echo "Please install uv first. See: https://github.com/astral-sh/uv"
    echo "For example, you can often install it with: pip install uv"
    exit 1
else
    echo "✅ uv found: $(command -v uv)"
fi

# --- Check for Poetry ---
if ! command -v poetry &> /dev/null; then
    echo "❌ Error: Poetry is not installed."
    echo "Please install Poetry first. See: https://python-poetry.org/docs/#installation"
    exit 1
else
    echo "✅ Poetry found: $(command -v poetry)"
fi

VENV_DIR=".venv"
REQUIREMENTS_FILE="requirements.txt"

# --- Create Virtual Environment with uv ---
if [ -d "$VENV_DIR" ]; then
    echo "ℹ️ Existing virtual environment '$VENV_DIR' found. Skipping creation."
else
    echo "🐍 Creating virtual environment in '$VENV_DIR' using uv..."
    uv venv "$VENV_DIR"
    echo "✅ Virtual environment created."
fi

# --- Activate Virtual Environment (for subsequent commands in this script) ---
# Note: This activates it for the current script's execution context.
# The user will need to activate it separately in their terminal for manual use.
source "$VENV_DIR/bin/activate"
echo "✅ Virtual environment activated for script execution."

# --- Export Dependencies using Poetry ---
echo "📦 Exporting dependencies from pyproject.toml to $REQUIREMENTS_FILE using Poetry..."
# Export production dependencies. Add --dev if development dependencies are also needed.
# Using --without-credentials to avoid any potential credential leakage if plugins use them in pyproject.toml
poetry export -f requirements.txt --output "$REQUIREMENTS_FILE" --without-hashes --without-credentials
echo "✅ Dependencies exported."

# --- Install Dependencies with uv ---
echo "💾 Installing dependencies from $REQUIREMENTS_FILE using uv..."
uv pip install -r "$REQUIREMENTS_FILE"
echo "✅ Dependencies installed."

# --- Cleanup (Optional: remove requirements.txt) ---
# echo "🧹 Cleaning up temporary $REQUIREMENTS_FILE..."
# rm "$REQUIREMENTS_FILE"
# echo "✅ Cleanup complete."
# Decided to keep requirements.txt for now, can be added to .gitignore

echo ""
echo "🎉 Installation complete!"
echo "To activate the virtual environment in your terminal, run:"
echo "source $VENV_DIR/bin/activate"
echo ""
echo "You can then run the application using 'run_macos.sh' (once created)."

exit 0
