#!/bin/bash
# Deployment script for Raspberry Pi 5
# Run this script on your Raspberry Pi to set up the sign detection system

set -e

echo "=================================="
echo "Sign Detection System - Pi Setup"
echo "=================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo -e "${RED}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo -e "${BLUE}Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Install Node.js (if not installed)
if ! command -v node &> /dev/null; then
    echo -e "${BLUE}Installing Node.js...${NC}"
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Install Python dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
sudo apt-get install -y python3-pip python3-opencv python3-numpy

# Install picamera2 for Raspberry Pi camera
echo -e "${BLUE}Installing picamera2...${NC}"
sudo apt-get install -y python3-picamera2

# Install backend dependencies
echo -e "${BLUE}Installing Node.js backend dependencies...${NC}"
cd backend
npm install
cd ..

# Install Python packages
echo -e "${BLUE}Installing Python packages...${NC}"
cd backend/python
pip3 install -r requirements.txt --break-system-packages
cd ../..

# Check for trained model
if [ ! -f "backend/python/model/best.pt" ]; then
    echo -e "${RED}Warning: Custom trained model not found at backend/python/model/best.pt${NC}"
    echo "The system will use YOLOv8n pretrained model instead."
    echo "To use your custom model, copy it to: backend/python/model/best.pt"
fi

# Build frontend
echo -e "${BLUE}Building React frontend...${NC}"
cd frontend
npm install
npm run build
cd ..

# Create systemd services
echo -e "${BLUE}Creating systemd services...${NC}"

# Python camera server service
sudo tee /etc/systemd/system/sign-detection-camera.service > /dev/null <<EOF
[Unit]
Description=Sign Detection Camera Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)/backend/python
ExecStart=/usr/bin/python3 camera_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Node.js backend service
sudo tee /etc/systemd/system/sign-detection-backend.service > /dev/null <<EOF
[Unit]
Description=Sign Detection Node Backend
After=network.target sign-detection-camera.service
Requires=sign-detection-camera.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)/backend
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=3
Environment=PYTHON_SERVER=http://localhost:5001

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable sign-detection-camera.service
sudo systemctl enable sign-detection-backend.service

echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "To start the system:"
echo "  sudo systemctl start sign-detection-camera"
echo "  sudo systemctl start sign-detection-backend"
echo ""
echo "To check status:"
echo "  sudo systemctl status sign-detection-camera"
echo "  sudo systemctl status sign-detection-backend"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u sign-detection-camera -f"
echo "  sudo journalctl -u sign-detection-backend -f"
echo ""
echo "Access the dashboard at: http://localhost:5000"
echo ""
