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

# Poetry is no longer required for installation - using uv instead

VENV_DIR=".venv"

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

# --- Install Dependencies with uv directly from pyproject.toml ---
echo "💾 Installing dependencies for Auto Archiver Slack Bot using uv..."
# Install main dependencies plus Slack bot requirements
uv pip install -e .[slack]
echo "✅ Dependencies installed (including Slack bot support)."

# --- No cleanup needed ---
# Dependencies are installed directly from pyproject.toml, so no temporary files to clean up

echo ""
echo "🎉 Auto Archiver Slack Bot installation complete!"
echo ""
echo "📋 Next steps to set up your Slack bot:"
echo "1. Activate the virtual environment:"
echo "   source $VENV_DIR/bin/activate"
echo ""
echo "2. Create your .env file with Slack tokens:"
echo "   cp .env.example .env  # (if available)"
echo "   # Then edit .env with your SLACK_BOT_TOKEN and SLACK_APP_TOKEN"
echo ""
echo "3. Test the auto-archiver command:"
echo "   auto-archiver --help"
echo ""
echo "4. Run your Slack bot:"
echo "   python slack_bot.py"
echo ""
echo "📚 See the README.md for detailed Slack app setup instructions."

exit 0
