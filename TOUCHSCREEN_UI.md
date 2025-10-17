# Touchscreen UI Guide

## Overview

The Sign Detection System has been redesigned for optimal use on a **2.8" LCD touchscreen** with a resolution of **640x480 pixels**.

## Home Screen

The main menu displays 4 large, touch-friendly buttons arranged horizontally:

```
┌─────────────────────────────────────────────────────────┐
│  🚦 Sign Detection                        ●  Offline    │
├─────────────────────────────────────────────────────────┤
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐              │
│  │  📹  │  │  🚗  │  │  ⚙️  │  │  📋  │              │
│  │      │  │      │  │      │  │      │              │
│  │ Live │  │Drive │  │ Set  │  │ Logs │              │
│  │ Feed │  │ Mode │  │tings │  │      │              │
│  └──────┘  └──────┘  └──────┘  └──────┘              │
└─────────────────────────────────────────────────────────┘
```

### Button Layout
- **Button 1: Live Feed** 📹 - View real-time detection with bounding boxes
- **Button 2: Driving Mode** 🚗 - Choose between Casual or Gamified modes
- **Button 3: Settings** ⚙️ - Configure camera and detection parameters
- **Button 4: Logs** 📋 - View detection and system logs

## Pages

### 1. Live Feed Page

**Purpose:** View real-time camera feed with YOLO detection overlays

**Layout:**
```
┌─────────────────────────────────────────┐
│ ← Back        Live Feed                 │
├─────────────────────────────────────────┤
│ [▶ Start] [⏹ Stop] [📷]                │
├─────────────────────────────────────────┤
│                                          │
│         Video Feed Area                  │
│         (640x340 pixels)                │
│                                          │
├─────────────────────────────────────────┤
│ FPS: 30    Detected: 5                  │
└─────────────────────────────────────────┘
```

**Controls:**
- **▶ Start** - Start the camera and detection
- **⏹ Stop** - Stop the camera
- **📷 Capture** - Save current frame with detections
- **← Back** - Return to home screen

**Stats Bar:**
- **FPS** - Current frames per second
- **Detected** - Number of objects detected in current frame

### 2. Driving Mode Page

**Purpose:** Select between two driving assistance modes

**Layout:**
```
┌─────────────────────────────────────────┐
│ ← Back        Driving Mode              │
├─────────────────────────────────────────┤
│                                          │
│  ┌──────────────┐  ┌──────────────┐   │
│  │      🚙      │  │      🏆      │   │
│  │              │  │              │   │
│  │ Casual Mode  │  │ Gamified     │   │
│  │              │  │    Mode      │   │
│  │ Simple       │  │ Score &      │   │
│  │ detection    │  │ achievements │   │
│  │ display      │  │              │   │
│  └──────────────┘  └──────────────┘   │
│                                          │
└─────────────────────────────────────────┘
```

**Modes:**

#### Casual Mode 🚙
- Clean, simple detection display
- Focus on safety and clarity
- Minimal distractions
- Real-time sign detection feedback

#### Gamified Mode 🏆
- Score points for detected signs
- Achievement system
- Progress tracking
- Engaging visual feedback

**Status:** Coming Soon (placeholder implemented)

### 3. Settings Page

**Purpose:** Configure camera and detection parameters

**Layout:**
```
┌─────────────────────────────────────────┐
│ ← Back        Settings                  │
├─────────────────────────────────────────┤
│ Camera                                   │
│   Resolution    [640x480 ▼]            │
│   FPS           [30 ▼]                  │
│                                          │
│ Detection                                │
│   Confidence    [━━━●━━━━━] 50%        │
│                                          │
│ [💾 Save]  [🔄 Reload]                 │
└─────────────────────────────────────────┘
```

**Settings:**

**Camera:**
- **Resolution** - Select from 640x480, 800x600, 1280x720
- **FPS** - Frame rate: 15, 30, or 60

**Detection:**
- **Confidence** - Threshold slider (0-100%)

**Controls:**
- **💾 Save** - Save settings to config.json (applies automatically)
- **🔄 Reload** - Reload settings from server

### 4. Logs Page

**Purpose:** View detection and system logs

**Layout:**
```
┌─────────────────────────────────────────┐
│ ← Back        Detection Logs            │
├─────────────────────────────────────────┤
│ [🔄] [🗑️] [Filter: All ▼]             │
├─────────────────────────────────────────┤
│ 2025-10-17 01:23:45 - INFO - Camera... │
│ 2025-10-17 01:23:46 - INFO - Detect... │
│ 2025-10-17 01:23:47 - INFO - Found ... │
│ 2025-10-17 01:23:48 - WARN - Low co... │
│ 2025-10-17 01:23:49 - INFO - FPS: 30   │
│ ...                                      │
└─────────────────────────────────────────┘
```

**Controls:**
- **🔄 Refresh** - Reload logs from server
- **🗑️ Clear** - Clear display (doesn't delete log files)
- **Filter** - Show All, INFO, WARN, or ERROR only

## Touchscreen Optimizations

### Button Sizes
- **Menu buttons:** Full column height (~380px)
- **Control buttons:** Minimum 50px height, 80px width
- **Touch target:** All buttons have adequate spacing (12px gaps)

### Typography
- **Header:** 24px
- **Button labels:** 16-18px
- **Body text:** 14-16px
- **Stats:** 14px

### Colors & Contrast
- **Dark theme** - Easier on eyes, better for night driving
- **High contrast** - White text on dark background
- **Color coding:**
  - Blue: Primary actions
  - Green: Success/Start
  - Red: Danger/Stop
  - Gray: Secondary actions

### Gestures
- **Tap** - Primary interaction (no hover states needed)
- **Active feedback** - Buttons scale down slightly on tap (0.95x)
- **No swipe gestures** - All navigation via buttons

## Configuration

The UI automatically adjusts to the 640x480 resolution. Key CSS settings:

```css
body {
    width: 640px;
    height: 480px;
    overflow: hidden;
}

.menu-buttons {
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}

.video-container-compact {
    width: 640px;
    height: 340px;
}
```

## Navigation Flow

```
        ┌─────────┐
        │  Home   │
        └────┬────┘
             │
    ┌────────┼────────┬────────┐
    │        │        │        │
    ▼        ▼        ▼        ▼
┌────────┐ ┌────┐ ┌────┐ ┌────┐
│  Live  │ │Drive│ │Set │ │Logs│
│  Feed  │ │Mode │ │tings│ │   │
└────────┘ └────┘ └────┘ └────┘
    │        │       │       │
    └────────┴───────┴───────┘
             │
             ▼
        ← Back to Home
```

## Best Practices

### For Raspberry Pi LCD Touchscreen

1. **Disable Screen Saver**
   ```bash
   sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
   # Add these lines:
   @xset s off
   @xset -dpms
   @xset s noblank
   ```

2. **Auto-start Browser in Kiosk Mode**
   ```bash
   # Add to autostart:
   @chromium-browser --kiosk --app=http://localhost:5000
   ```

3. **Rotate Screen (if needed)**
   ```bash
   # In /boot/config.txt:
   display_rotate=1  # 90 degrees
   display_rotate=2  # 180 degrees
   display_rotate=3  # 270 degrees
   ```

4. **Calibrate Touch**
   ```bash
   sudo apt-get install xinput-calibrator
   xinput_calibrator
   ```

### Performance Tips

- Use **640x480** resolution for best performance
- Set **FPS to 15-30** for Raspberry Pi
- Enable **GPU acceleration** in config.json
- Use **yolov8n.pt** (nano model) for faster detection

## Keyboard Shortcuts (Development)

When testing on desktop with keyboard:

- **H** - Go to Home
- **1** - Live Feed
- **2** - Driving Mode
- **3** - Settings
- **4** - Logs
- **Space** - Start/Stop camera (on Live Feed page)
- **C** - Capture (on Live Feed page)
- **Esc** - Back to Home

*(Note: Shortcuts not implemented yet - touch-only for now)*

## Browser Requirements

- **Chromium** (Recommended for Raspberry Pi)
- **Chrome/Edge** (Windows/Mac development)
- **Firefox** (Supported)
- **Safari** (iOS - touch optimized)

### Required Features
- WebSocket support
- Canvas API
- ES6 JavaScript
- CSS Grid
- Flexbox

## Troubleshooting

### Buttons Too Small
Increase button sizes in CSS:
```css
.menu-btn {
    min-height: 100px;  /* Increase from default */
}
```

### Text Too Small
Adjust font sizes in CSS variables:
```css
.menu-btn .label {
    font-size: 18px;  /* Increase from 16px */
}
```

### Touch Not Responsive
1. Check `touch-action: manipulation` is set
2. Verify no conflicting hover states
3. Test with `pointer-events: auto`

### Video Feed Cut Off
Adjust video container height:
```css
.video-container-compact {
    height: 340px;  /* Adjust as needed */
}
```

## Future Enhancements

- [ ] Implement Casual Driving Mode
- [ ] Implement Gamified Driving Mode
- [ ] Add haptic feedback (vibration on button press)
- [ ] Save UI preferences
- [ ] Dark/Light theme toggle
- [ ] Multi-language support
- [ ] Voice commands
- [ ] Gesture navigation

## Files Modified

- `frontend/templates/index.html` - Main HTML structure
- `frontend/static/css/style.css` - Touchscreen-optimized styles
- `frontend/static/js/app.js` - Navigation and interaction logic
- `TOUCHSCREEN_UI.md` - This documentation

## Support

For issues or questions about the touchscreen UI:
1. Check logs in `data/logs/app.log`
2. Verify resolution: `640x480`
3. Test on desktop browser first
4. Review browser console for errors
