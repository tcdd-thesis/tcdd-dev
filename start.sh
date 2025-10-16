#!/bin/bash
# Start Sign Detection System (Linux/Raspberry Pi)

echo "==================================="
echo "Sign Detection System"
echo "==================================="

# Navigate to project root
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: No virtual environment found"
    echo "Run: python -m venv venv && source venv/bin/activate && pip install -r backend/requirements.txt"
fi

# Create necessary directories
mkdir -p data/logs
mkdir -p data/captures
mkdir -p backend/models

# Start the server
echo ""
echo "Starting server..."
echo "Access the app at: http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

cd backend
python main.py
