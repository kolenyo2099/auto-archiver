#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
# set -e # Commented out as 'source' might return non-zero if .venv doesn't exist, handled by explicit check

VENV_DIR=".venv"

echo "🚀 Attempting to start Auto Archiver applications..."

# --- Check for Virtual Environment ---
if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "❌ Error: Virtual environment '$VENV_DIR' not found or is incomplete."
    echo "Please run the './install_macos.sh' script first to set up the environment."
    exit 1
fi

# --- Activate Virtual Environment ---
echo "🐍 Activating virtual environment from '$VENV_DIR'..."
source "$VENV_DIR/bin/activate"
echo "✅ Virtual environment activated."

# Re-enable 'set -e' after successful activation if desired for subsequent commands
set -e

# --- Start the UI Backend Flask Application ---
UI_BACKEND_SCRIPT="src/auto_archiver/ui_backend.py"

if [ ! -f "$UI_BACKEND_SCRIPT" ]; then
    echo "❌ Error: UI Backend script not found at '$UI_BACKEND_SCRIPT'."
    echo "Please ensure the project structure is correct."
    exit 1
fi

echo "🌐 Starting the Extractor UI Backend (Flask App)..."
echo "You can access the UI at http://localhost:5001 (or the configured host/port) once it starts."
echo "Press Ctrl+C to stop the UI Backend."

# The ui_backend.py script has its own default host/port and debug settings.
# These can be overridden by FLASK_HOST, FLASK_PORT, FLASK_DEBUG environment variables.
# Example: export FLASK_DEBUG=false if you don't want debug mode
python "$UI_BACKEND_SCRIPT" &
UI_BACKEND_PID=$!

echo "✅ UI Backend started with PID: $UI_BACKEND_PID."
echo "(Note: If you see an error immediately above like 'Address already in use', the port might be taken.)"
echo ""

# --- Instructions for running the main Auto Archiver application ---
echo "⚙️ To run the main Auto Archiver application (e.g., orchestrator, feeders):"
echo "1. Open a new terminal window/tab."
echo "2. Activate the virtual environment: source $VENV_DIR/bin/activate"
echo "3. Run auto_archiver commands, for example:"
echo "   auto_archiver orchestrate --config path/to/your/config.yaml"
echo "   auto_archiver feed --feeder-name your_feeder --url \"some_url\"" # Escaped quotes for clarity
echo "   (Refer to the project's documentation for detailed command usage.)"
echo ""

# --- Wait for UI Backend to terminate (optional, or just let it run) ---
# This script will now wait for the UI backend process.
# If you want this script to exit and leave the UI backend running,
# you can remove the 'wait' command and the trap.
# However, this makes it easier to stop both with Ctrl+C if this script is the main entry point.

# Function to clean up background process on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down UI Backend (PID: $UI_BACKEND_PID)..."
    # Check if process exists before killing
    if ps -p $UI_BACKEND_PID > /dev/null; then
       kill $UI_BACKEND_PID
       echo "✅ UI Backend (PID: $UI_BACKEND_PID) signaled to terminate."
    else
       echo "ℹ️ UI Backend (PID: $UI_BACKEND_PID) already terminated."
    fi
    # Add any other cleanup commands here
}

# Trap SIGINT (Ctrl+C) and SIGTERM to run cleanup
trap cleanup SIGINT SIGTERM

echo "ℹ️ This script will keep running to keep the UI backend active."
echo "   Press Ctrl+C in this terminal to stop the UI Backend and this script."

# Wait for the process and capture its exit status
wait $UI_BACKEND_PID
WAIT_STATUS=$?

echo "🏁 UI Backend process exited with status $WAIT_STATUS."
echo "🏁 Script finished."

exit $WAIT_STATUS
