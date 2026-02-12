# Auto-Start Guide for TCDD Sign Detection System

This guide explains how to configure your Raspberry Pi to automatically start the Sign Detection System when the Pi boots up, and how to manage the service.

## Table of Contents

1. [Overview](#overview)
2. [How Systemd Services Work](#how-systemd-services-work)
3. [Installation Steps](#installation-steps)
4. [Service Management Commands](#service-management-commands)
5. [Viewing Logs](#viewing-logs)
6. [Troubleshooting](#troubleshooting)
7. [Customization](#customization)

---

## Overview

The Sign Detection System uses **systemd**, the standard service manager on Raspberry Pi OS (and most modern Linux distributions), to:

- **Auto-start** the application when the Raspberry Pi boots
- **Auto-restart** the application if it crashes
- **Manage** the application lifecycle (start, stop, restart)
- **Log** all application output to the system journal

---

## How Systemd Services Work

### What is Systemd?

Systemd is a system and service manager for Linux. It initializes the system and manages services (called "units") that run in the background.

### Service File Structure

The service file (`tcdd-detector.service`) contains several sections:

```ini
[Unit]
Description=TCDD Sign Detection System    # Human-readable description
After=network.target                       # Start after network is available
Wants=network-online.target               # Prefer online network

[Service]
Type=simple                               # Simple foreground process
User=pi                                   # Run as user 'pi'
WorkingDirectory=/home/pi/tcdd-dev        # Working directory
ExecStart=...                             # Command to start the service
Restart=always                            # Always restart if stopped
RestartSec=5                              # Wait 5 seconds before restart

[Install]
WantedBy=multi-user.target                # Enable at multi-user runlevel
```

### Service Lifecycle

1. **Boot** → Systemd starts
2. **Network Ready** → `network.target` reached
3. **Service Starts** → `tcdd-detector.service` starts
4. **Application Runs** → Flask server serving requests
5. **If Crash** → Systemd waits 5 seconds, then restarts
6. **Shutdown/Reboot** → Systemd sends SIGTERM, waits 30s, then SIGKILL

---

## Installation Steps

### Prerequisites

1. Raspberry Pi with Raspberry Pi OS installed
2. TCDD Sign Detection System installed at `/home/pi/tcdd-dev`
3. Python virtual environment set up at `/home/pi/tcdd-dev/venv`
4. All dependencies installed

### Step 1: Copy the Project to Raspberry Pi

If you haven't already, copy the project to your Raspberry Pi:

```bash
# From your development machine
scp -r tcdd-dev pi@<raspberry-pi-ip>:/home/pi/
```

### Step 2: Set Up the Virtual Environment

```bash
# SSH into the Raspberry Pi
ssh pi@<raspberry-pi-ip>

# Navigate to project directory
cd /home/pi/tcdd-dev

# Create virtual environment (if not exists)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### Step 3: Copy the Service File

```bash
# Copy service file to systemd directory
sudo cp /home/pi/tcdd-dev/tcdd-detector.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload
```

### Step 4: Enable Auto-Start

```bash
# Enable the service to start on boot
sudo systemctl enable tcdd-detector.service
```

You should see output like:
```
Created symlink /etc/systemd/system/multi-user.target.wants/tcdd-detector.service → /etc/systemd/system/tcdd-detector.service.
```

### Step 5: Start the Service

```bash
# Start the service now
sudo systemctl start tcdd-detector.service

# Check status
sudo systemctl status tcdd-detector.service
```

You should see:
```
● tcdd-detector.service - TCDD Sign Detection System
     Loaded: loaded (/etc/systemd/system/tcdd-detector.service; enabled; ...)
     Active: active (running) since ...
```

### Step 6: Test Auto-Start

```bash
# Reboot the Raspberry Pi
sudo reboot
```

After the Pi boots up, the application should be running automatically. Access it at:
```
http://<raspberry-pi-ip>:5000
```

---

## Service Management Commands

### Basic Commands

| Command | Description |
|---------|-------------|
| `sudo systemctl start tcdd-detector` | Start the service |
| `sudo systemctl stop tcdd-detector` | Stop the service |
| `sudo systemctl restart tcdd-detector` | Restart the service |
| `sudo systemctl status tcdd-detector` | Check service status |
| `sudo systemctl enable tcdd-detector` | Enable auto-start on boot |
| `sudo systemctl disable tcdd-detector` | Disable auto-start on boot |

### Check if Service is Enabled

```bash
sudo systemctl is-enabled tcdd-detector
# Output: enabled or disabled
```

### Check if Service is Active

```bash
sudo systemctl is-active tcdd-detector
# Output: active, inactive, or failed
```

---

## Viewing Logs

### View Recent Logs

```bash
# View last 50 lines
sudo journalctl -u tcdd-detector -n 50

# View last 100 lines with no pager
sudo journalctl -u tcdd-detector -n 100 --no-pager
```

### Follow Logs in Real-Time

```bash
sudo journalctl -u tcdd-detector -f
```

### View Logs from Current Boot

```bash
sudo journalctl -u tcdd-detector -b
```

### View Logs from Specific Time

```bash
# Last hour
sudo journalctl -u tcdd-detector --since "1 hour ago"

# Today
sudo journalctl -u tcdd-detector --since today

# Specific date/time
sudo journalctl -u tcdd-detector --since "2025-02-10 10:00:00"
```

### Export Logs to File

```bash
sudo journalctl -u tcdd-detector --since today > ~/tcdd-logs.txt
```

---

## Troubleshooting

### Service Won't Start

1. **Check the status:**
   ```bash
   sudo systemctl status tcdd-detector
   ```

2. **Check for errors in logs:**
   ```bash
   sudo journalctl -u tcdd-detector -n 100 --no-pager
   ```

3. **Common issues:**
   - Python virtual environment not found → Check path in service file
   - Missing dependencies → Activate venv and run `pip install -r requirements.txt`
   - Permission issues → Check that `User=pi` has access to all files
   - Port already in use → Check if another process is using port 5000

### Service Keeps Restarting

Check the logs to find the crash reason:
```bash
sudo journalctl -u tcdd-detector -n 200 --no-pager | grep -i error
```

### Modify the Service File

After modifying `/etc/systemd/system/tcdd-detector.service`:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Restart the service
sudo systemctl restart tcdd-detector
```

### Reset Failed State

If the service is in a failed state:
```bash
sudo systemctl reset-failed tcdd-detector
sudo systemctl start tcdd-detector
```

---

## Customization

### Change Installation Path

If your project is in a different location, edit the service file:

```bash
sudo nano /etc/systemd/system/tcdd-detector.service
```

Update these lines:
```ini
WorkingDirectory=/your/custom/path/tcdd-dev
Environment="PATH=/your/custom/path/tcdd-dev/venv/bin:..."
ExecStart=/your/custom/path/tcdd-dev/venv/bin/python /your/custom/path/tcdd-dev/backend/main.py
ReadWritePaths=/your/custom/path/tcdd-dev/data
ReadWritePaths=/your/custom/path/tcdd-dev/backend/models
```

### Change the User

If running as a different user:

```ini
User=yourusername
Group=yourusername
```

### Adjust Resource Limits

```ini
# Maximum memory (default: 512MB)
MemoryMax=1G

# CPU quota (default: 80%)
CPUQuota=100%
```

### Disable Security Hardening

If you encounter permission issues, you can remove these lines:
```ini
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=...
```

### Change Restart Behavior

```ini
# Never restart
Restart=no

# Only restart on failure
Restart=on-failure

# Restart on any exit
Restart=always

# Time to wait before restart (default: 5 seconds)
RestartSec=10
```

---

## Quick Reference Card

```bash
# === Installation ===
sudo cp tcdd-detector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tcdd-detector
sudo systemctl start tcdd-detector

# === Daily Use ===
sudo systemctl status tcdd-detector    # Check status
sudo systemctl restart tcdd-detector   # Restart app
sudo journalctl -u tcdd-detector -f    # Follow logs

# === If Something Goes Wrong ===
sudo journalctl -u tcdd-detector -n 100 --no-pager  # View recent logs
sudo systemctl stop tcdd-detector                    # Stop service
sudo systemctl reset-failed tcdd-detector            # Clear failed state
sudo systemctl start tcdd-detector                   # Start again
```

---

## Integration with UI Controls

The Sign Detection System's web interface includes three system control buttons:

1. **Shutdown App (⏻)** - Gracefully stops the Flask server
   - The service will automatically restart after 5 seconds (by design)
   - To permanently stop: use `sudo systemctl stop tcdd-detector`

2. **Shutdown Pi (⏼)** - Powers off the Raspberry Pi
   - Cleanly stops the camera and app before shutdown
   - Requires physical power cycle to restart

3. **Reboot Pi (↻)** - Reboots the Raspberry Pi
   - After reboot, the service auto-starts
   - The app will be available again within ~30-60 seconds

---

## Security Notes

- The service runs as user `pi`, not as root
- System commands (`shutdown`, `reboot`) require sudo privileges
- The app is configured to run with sudo (`sudo python main.py`) for hardware access
- Consider setting up passwordless sudo for specific commands if needed

---

## Support

If you encounter issues not covered in this guide:

1. Check the application logs: `data/logs/app.log`
2. Check the system journal: `sudo journalctl -u tcdd-detector`
3. Verify file permissions: `ls -la /home/pi/tcdd-dev/`
4. Test manual startup: `cd /home/pi/tcdd-dev && source venv/bin/activate && python backend/main.py`
