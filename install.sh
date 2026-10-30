#!/bin/bash
# Installs (or removes) the menu entry, login autostart entry and icon for
# Audio Keep-Alive, for the current user only.
#
#   ./install.sh              install menu entry + autostart at login
#   ./install.sh --uninstall  remove everything this script installed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"

APP_ID="audiokeepalive"
MENU_FILE="$DATA_DIR/applications/$APP_ID.desktop"
AUTOSTART_FILE="$CONFIG_DIR/autostart/$APP_ID.desktop"
ICON_FILE="$DATA_DIR/icons/hicolor/scalable/apps/$APP_ID.svg"

refresh_caches() {
	update-desktop-database "$DATA_DIR/applications" 2>/dev/null
	gtk-update-icon-cache -q -t "$DATA_DIR/icons/hicolor" 2>/dev/null
	return 0
}

if [ "$1" = "--uninstall" ]; then
	rm -f "$MENU_FILE" "$AUTOSTART_FILE" "$ICON_FILE"
	refresh_caches
	echo "Removed menu entry, autostart entry and icon."
	exit 0
fi

mkdir -p "$(dirname "$MENU_FILE")" "$(dirname "$AUTOSTART_FILE")" "$(dirname "$ICON_FILE")"
cp "$SCRIPT_DIR/icons/$APP_ID.svg" "$ICON_FILE"

# Menu entry: appears under "Sound & Video" in the Mint menu.
cat > "$MENU_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Audio Keep-Alive
Comment=Play periodic tones to keep an auto-sleeping speaker awake
Exec="$SCRIPT_DIR/run.sh"
Icon=$APP_ID
Terminal=false
Categories=AudioVideo;Audio;
Keywords=speaker;soundbar;sleep;tone;
StartupNotify=false
DESKTOP

# Autostart entry: starts hidden in the tray at login. The delay lets the
# panel's tray and the audio server settle before the first tone is played.
cat > "$AUTOSTART_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Audio Keep-Alive
Comment=Play periodic tones to keep an auto-sleeping speaker awake
Exec="$SCRIPT_DIR/run.sh" --hidden
Icon=$APP_ID
Terminal=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=20
DESKTOP

refresh_caches
echo "Installed:"
echo "  $MENU_FILE"
echo "  $AUTOSTART_FILE"
echo "  $ICON_FILE"
