# Audio Keep-Alive Desktop App

A Qt-based desktop application for Linux Mint that plays two tones at a set interval (every 60 seconds by default) to keep your soundbar from auto-shutting down due to lack of audio playback.

## Features

- **Start/Stop Control**: Toggle audio playback on and off
- **Auto-Start**: Automatically begins playing tones when the application launches
- **Volume Control**: Adjust playback volume (0-100%)
- **Interval Adjustment**: Change the time between tone plays (1-600 seconds)
- **Frequency Control**: Adjust both tone frequencies (20-20000 Hz)
- **Status Display**: Shows current status and countdown to next play
- **System Tray Integration**: Hide window to tray (via minimize button or menu), click tray icon to restore, and control from system tray menu
- **Settings Persistence**: Saves your preferences automatically
- **Reliable Long-Running Playback**: Tones play through one continuous audio stream; if it exits or stalls it is restarted automatically — no app restart required

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

   **Menu entry and start at login:**
   ```bash
   ./install.sh
   ```
   This adds **Audio Keep-Alive** to the Mint menu (under *Sound & Video*) and registers it to start at login, hidden in the system tray. It can be toggled later in *Startup Applications*. Run `./install.sh --uninstall` to remove both. Re-run `./install.sh` if you move the project folder.

   Only one instance runs at a time: launching it again just brings up the existing window. Pass `--hidden` to start in the tray without showing the window.

2. **Controls**:
   - Click **Start/Stop** to toggle playback
   - Adjust **Volume** slider to change playback volume
   - Change **Interval** to modify time between plays (keep it shorter than your soundbar's auto-off time)
   - Adjust **Tone 1** and **Tone 2** frequencies
   - Changes to volume, interval or frequency apply as soon as the control settles: the stream restarts, the tones play straight away and the countdown resets
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

The app also uses these files:
- `~/.cache/audiokeepalive/cycle.wav` - the rendered interval it loops, rewritten on each stream start (about 5.8 MB per minute of interval, so up to about 58 MB)
- `~/.local/state/audiokeepalive/audiokeepalive.log` - the log, limited to about 1 MB plus one rotated copy

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

The app is designed to recover from this on its own:
- One interval (tone, tone, silence) is rendered to `~/.cache/audiokeepalive/cycle.wav` and looped forever by a single `play` process, so the audio connection is made once rather than for every tone.
- If `play` exits, or stops reporting progress for 15 seconds, it is restarted with a growing delay of up to 30 seconds.
- While a failure is active the status shows **"Running (audio error)"** and the tray icon changes to a warning. Both clear when audio resumes.

If audio still stops:
- Check the log: `~/.local/state/audiokeepalive/audiokeepalive.log`. It records every stream start, failure and recovery, plus anything `play` reports.
- Check the stream is running: `ps aux | grep "cycle.wav repeat" | grep -v grep`. Exactly one is expected during playback.
- As a last resort, restart the application — it will clean up any orphaned stream on startup.

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
├── audio_player.py      # Renders the tone cycle and runs the looping SoX stream
├── tray_icon.py         # System tray icon and menu
├── settings.py          # Settings persistence manager
├── run.sh               # Launcher script (uses venv automatically)
├── install.sh           # Installs menu entry, login autostart and icon
├── icons/               # Application / tray icon
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── venv/                # Virtual environment (created during setup)
```

## License

This project is licensed under the MIT License.

Copyright (c) 2026 spuddermax

See the [LICENSE](LICENSE) file for details.
