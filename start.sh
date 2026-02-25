#!/bin/bash
# Start Sign Detection System (Linux/Raspberry Pi)

# Navigate to project root
cd "$(dirname "$0")"

# Check if chromium-browser is installed
if ! command -v chromium-browser &> /dev/null; then
    echo "Error: chromium-browser not found!"
    echo "Please install it with: sudo apt install chromium-browser"
    exit 1
fi

# Check if config.json exists
if [ ! -f "config.json" ]; then
    echo "Error: config.json not found! Creating from template..."
    sed -E 's|//.*||; s/[[:space:]]+$//; /^[[:space:]]*$/d' config-template-json.txt > config.json
fi

# Load configuration from config.json
CONFIG=$(cat config.json)

# --- Dev mode check ---
# When dev_mode is true, abort automatic startup (e.g. when launched by systemd).
# The user can still run the backend manually during development.
DEV_MODE=$(echo "$CONFIG" | grep -oP '"dev_mode"\s*:\s*\K(true|false)')
if [ "$DEV_MODE" = "true" ] && [ -n "$INVOCATION_ID" ]; then
    echo "Dev mode is enabled — automatic startup aborted."
    exit 0
fi

# Extract virtual environment path from config.json, exit if no value found
if echo "$CONFIG" | grep -q '"venv_path":\s*"\K[^"]+'; then
    echo "Error: 'venv_path' not found in config.json!"
    exit 1
fi
VENV_PATH=$(echo "$CONFIG" | grep -oP '"venv_path":\s*"\K[^"]+')

# Activate virtual environment if it exists
if [ -d "$VENV_PATH" ]; then
    echo "Activating virtual environment in $VENV_PATH..."
    source "$VENV_PATH/bin/activate"
else
    echo "Warning: No virtual environment found"
    echo "Run: python -m venv $VENV_PATH && source $VENV_PATH/bin/activate && pip install -r backend/requirements.txt"
    exit 1
fi

# Create necessary directories
mkdir -p data/logs
mkdir -p data/captures
mkdir -p backend/models

# Start Python backend in background
python backend/main.py &
BACKEND_PID=$!

# Wait for server to be ready
sleep 5

# Start browser with touch support enabled
chromium-browser \
    --kiosk \
    --touch-events=enabled \
    --enable-pinch \
    --enable-features=TouchpadOverscrollHistoryNavigation \
    --disable-pinch \
    --overscroll-history-navigation=0 \
    --password-store=basic \
    http://localhost:5000 &

# Bring Python logs back to foreground
wait $BACKEND_PID