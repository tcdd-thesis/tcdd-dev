#!/bin/bash
# Development start script - runs all services locally

echo "Starting Sign Detection System in Development Mode"
echo "==================================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Trap Ctrl+C to kill all background processes
trap 'kill $(jobs -p) 2>/dev/null; echo -e "\n${GREEN}Stopped all services${NC}"; exit' INT TERM

# Start Python camera server
echo -e "${BLUE}Starting Python camera server on port 5001...${NC}"
cd backend/python
python3 camera_server.py &
PYTHON_PID=$!
cd ../..

# Wait for Python server to start
sleep 3

# Start Node.js backend
echo -e "${BLUE}Starting Node.js backend on port 5000...${NC}"
cd backend
npm start &
NODE_PID=$!
cd ..

# Wait for backend to start
sleep 2

# Start React frontend
echo -e "${BLUE}Starting React frontend on port 3000...${NC}"
cd frontend
npm start &
REACT_PID=$!
cd ..

echo ""
echo -e "${GREEN}All services started!${NC}"
echo "================================"
echo "Python Camera Server: http://localhost:5001"
echo "Node.js Backend:      http://localhost:5000"
echo "React Frontend:       http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for all background processes
wait
