# Audio Keep-Alive Desktop App

A Qt-based desktop application for Linux Mint that plays two tones every 60 seconds to keep your soundbar from auto-shutting down due to lack of audio playback.

## Features

- **Start/Stop Control**: Toggle audio playback on and off
- **Auto-Start**: Automatically begins playing tones when the application launches
- **Volume Control**: Adjust playback volume (0-100%)
- **Interval Adjustment**: Change the time between tone plays (1-3600 seconds)
- **Frequency Control**: Adjust both tone frequencies (20-20000 Hz)
- **Status Display**: Shows current status and countdown to next play
- **System Tray Integration**: Minimize to tray and control from system tray menu
- **Settings Persistence**: Saves your preferences automatically

## Requirements

- Python 3.8 or higher
- PyQt6
- SoX (`sox` package) - must be installed system-wide

## Installation

1. **Install system dependencies** (required for Qt/X11):
   ```bash
   sudo apt install sox libxcb-cursor0 libxcb-xinerama0 libxcb-xfixes0 libxcb-xkb1 libxkbcommon-x11-0
   ```

2. **Set up Python virtual environment** (recommended for Linux Mint 22+):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

   **Note**: Linux Mint 22 uses externally-managed Python environments. Using a virtual environment is required to install Python packages.

## Usage

1. **Run the application** (recommended - using the launcher script):
   ```bash
   ./run.sh
   ```
   
   The launcher script automatically uses the virtual environment if available.

   **Alternative methods:**
   
   Manually activate the virtual environment and run:
   ```bash
   source venv/bin/activate
   python main.py
   ```
   
   Or use the virtual environment Python directly:
   ```bash
   ./venv/bin/python main.py
   ```

   **Note**: The application will automatically start playing tones when launched.

2. **Controls**:
   - Click **Start/Stop** to toggle playback
   - Adjust **Volume** slider to change playback volume
   - Change **Interval** to modify time between plays
   - Adjust **Tone 1** and **Tone 2** frequencies
   - Click **Minimize to Tray** to hide the window
   - Right-click the tray icon for quick access menu

3. **System Tray**:
   - The app runs in the system tray when minimized
   - Right-click the tray icon for options:
     - Show/Hide Window
     - Start/Stop playback
     - Quit

## Settings

Settings are automatically saved to `~/.config/audiokeepalive/settings.json` and include:
- Volume level
- Playback interval
- Tone frequencies
- Window position and size

## Default Values

- Volume: 30%
- Interval: 60 seconds
- Tone 1: 200 Hz
- Tone 2: 300 Hz

## Troubleshooting

**"SoX 'play' command not found" error:**
- Install SoX: `sudo apt install sox`
- Verify installation: `which play`

**System tray not available:**
- Ensure your desktop environment supports system tray
- On some systems, you may need to install additional packages

**No sound playing:**
- Check that your audio system is working: `play -n synth 0.2 sine 200`
- Verify volume levels in the app and system
- Check that SoX is properly installed

**"externally-managed-environment" error when installing:**
- This is expected on Linux Mint 22+. Use a virtual environment as shown in the Installation section above

**"Could not load the Qt platform plugin 'xcb'" error:**
- Install the required X11 libraries: `sudo apt install libxcb-cursor0 libxcb-xinerama0 libxcb-xfixes0 libxcb-xkb1 libxkbcommon-x11-0`
- These are Qt/X11 dependencies needed for PyQt6 to work with the X11 window system

**"AttributeError: 'QApplication' object has no attribute 'isSystemTrayAvailable'" error:**
- This was a bug in earlier versions. Make sure you're using the latest version of the code.
- The method should be called on `QSystemTrayIcon`, not `QApplication`

## Project Structure

```
AudioKeepAlive/
├── main.py              # Application entry point
├── main_window.py       # Main GUI window with all controls
├── audio_player.py      # SoX audio playback handler
├── tray_icon.py         # System tray icon and menu
├── settings.py          # Settings persistence manager
├── run.sh               # Launcher script (uses venv automatically)
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── venv/                # Virtual environment (created during setup)
```

## License

This project is provided as-is for personal use.
