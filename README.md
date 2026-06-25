# Audio Keep-Alive Desktop App

A Qt-based desktop application for Linux Mint that plays two tones every 60 seconds to keep your soundbar from auto-shutting down due to lack of audio playback.

## Features

- **Start/Stop Control**: Toggle audio playback on and off
- **Auto-Start**: Automatically begins playing tones when the application launches
- **Volume Control**: Adjust playback volume (0-100%)
- **Interval Adjustment**: Change the time between tone plays (1-3600 seconds)
- **Frequency Control**: Adjust both tone frequencies (20-20000 Hz)
- **Status Display**: Shows current status and countdown to next play
- **System Tray Integration**: Hide window to tray (via minimize button or menu), click tray icon to restore, and control from system tray menu
- **Settings Persistence**: Saves your preferences automatically
- **Reliable Long-Running Playback**: Playback runs without blocking the UI, the audio device is kept awake to prevent suspend-related stalls, and any hung `play` process is automatically terminated and recovered from on the next interval — no restart required

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
   
   **To run in the background:**
   ```bash
   ./run.sh &
   ```
   The script automatically handles backgrounding and will continue running even if you close the terminal.

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
   - Click **Minimize to Tray** to hide the window to the system tray
   - Click the **system minimize button** (title bar) to hide to tray
   - Click the **close button (X)** to hide to tray (app continues running)
   - Right-click the tray icon for quick access menu

3. **System Tray**:
   - The app runs in the system tray when the window is hidden
   - **Click the tray icon** to restore/show the window (single-click works)
   - Right-click the tray icon for options:
     - Show Window / Hide Window (toggles based on current state)
     - Start/Stop playback
     - Quit (exits the application)

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

**Audio stops working after running for a while:**

The app is designed to recover from this on its own, so a restart should rarely be needed:
- While playback is active, a continuous, near-silent keep-awake stream runs to stop the audio device from suspending between tones (suspend/resume races were the main cause of `play` getting stuck).
- Playback runs off the UI thread via `QProcess`, and any tone that hangs is automatically terminated (SIGTERM, escalating to SIGKILL) and retried on the next interval.
- On startup the app also clears any stuck `play` processes left over from a previous run.

If audio still stops:
- Watch for the status changing to **"Running (audio error)"** and a one-time "Playback Error" dialog — this indicates a tone failed to play.
- Check for stuck `play` processes: `ps aux | grep "play -n synth" | grep -v grep`. The persistent keep-awake process (`play -n synth 86400 sine 1 vol 0.0001`) is expected while playback is running; stop the app to clear it, or kill strays with `pkill -f "play -n synth"`.
- As a last resort, restart the application — it will clean up any stuck audio processes on startup.

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

This project is licensed under the MIT License.

Copyright (c) 2026 spuddermax

See the [LICENSE](LICENSE) file for details.
