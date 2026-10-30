#!/usr/bin/env python3
"""Audio Keep-Alive Desktop Application."""
import os
import sys
import time
import signal
import logging
import argparse
from logging.handlers import RotatingFileHandler
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon
from PyQt6.QtCore import Qt, QThread, QTimer
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from main_window import MainWindow
from tray_icon import TrayIcon, app_icon
from settings import Settings

# Local socket name used to enforce a single running instance per user.
INSTANCE_NAME = f"audiokeepalive-{os.getuid()}"

# How long to wait for the panel's tray when started at login.
TRAY_WAIT_SECONDS = 60

LOG_FILE = Path.home() / ".local" / "state" / "audiokeepalive" / "audiokeepalive.log"


def setup_logging():
	"""Log to a small rotating file, since the app has no terminal."""
	LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
	logging.basicConfig(
		level=logging.INFO,
		format="%(asctime)s %(levelname)s %(message)s",
		handlers=[RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=1)]
	)


def notify_running_instance(show_window: bool) -> bool:
	"""Return True if another instance is running, optionally raising it."""
	socket = QLocalSocket()
	socket.connectToServer(INSTANCE_NAME)
	if not socket.waitForConnected(500):
		return False
	if show_window:
		socket.write(b"show")
		socket.waitForBytesWritten(500)
	socket.disconnectFromServer()
	return True


def wait_for_tray(app, timeout_seconds: int) -> bool:
	"""Wait for the system tray to appear (it can lag behind at login)."""
	deadline = time.monotonic() + timeout_seconds
	while not QSystemTrayIcon.isSystemTrayAvailable():
		if time.monotonic() >= deadline:
			return False
		app.processEvents()
		QThread.msleep(250)
	return True


def main():
	"""Main application entry point."""
	parser = argparse.ArgumentParser(description="Audio Keep-Alive")
	parser.add_argument(
		"--hidden",
		action="store_true",
		help="start in the system tray without showing the window"
	)
	args, qt_args = parser.parse_known_args()

	# Enable high DPI scaling
	QApplication.setHighDpiScaleFactorRoundingPolicy(
		Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
	)
	
	app = QApplication(sys.argv[:1] + qt_args)
	app.setQuitOnLastWindowClosed(False)
	app.setApplicationName("Audio Keep-Alive")
	app.setDesktopFileName("audiokeepalive")
	app.setWindowIcon(app_icon())

	# Only one instance may run: a second one would kill the first one's
	# 'play' processes during startup cleanup. Launching again from the menu
	# just brings the existing window up instead.
	if notify_running_instance(show_window=not args.hidden):
		sys.exit(0)
	
	# Check if system tray is available
	if not wait_for_tray(app, TRAY_WAIT_SECONDS if args.hidden else 0):
		QMessageBox.critical(
			None,
			"System Tray",
			"System tray is not available on this system."
		)
		sys.exit(1)
	
	try:
		setup_logging()
		
		# Initialize components
		settings = Settings()
		tray_icon = TrayIcon()
		main_window = MainWindow(settings, tray_icon)
		
		# Connect signals
		def hide_window():
			"""Hide the main window."""
			main_window.hide()
			tray_icon.update_window_visibility(False)
		
		tray_icon.show_window.connect(main_window.show_and_raise)
		tray_icon.hide_window.connect(hide_window)
		tray_icon.toggle_playback.connect(main_window._toggle_playback)
		tray_icon.quit_requested.connect(app.quit)

		# Listen for later launches asking the running instance to show itself.
		instance_server = QLocalServer(app)
		QLocalServer.removeServer(INSTANCE_NAME)
		instance_server.listen(INSTANCE_NAME)

		def on_instance_connection():
			"""Show the window when another launch asks for it."""
			socket = instance_server.nextPendingConnection()
			socket.readyRead.connect(main_window.show_and_raise)
			socket.disconnected.connect(socket.deleteLater)

		instance_server.newConnection.connect(on_instance_connection)

		# Ensure the audio stream is killed on exit so it does not linger as
		# an orphaned 'play' process, including when asked to quit by a signal.
		app.aboutToQuit.connect(main_window.shutdown)
		signal.signal(signal.SIGTERM, lambda *_: app.quit())
		signal_timer = QTimer(app)
		signal_timer.timeout.connect(lambda: None)  # Lets Python see signals.
		signal_timer.start(500)
		
		# Show tray icon
		tray_icon.show()
		
		# Show main window, unless started hidden (e.g. autostart at login)
		if args.hidden:
			tray_icon.update_window_visibility(False)
		else:
			main_window.show()
			tray_icon.update_window_visibility(True)
		
		# Run application
		sys.exit(app.exec())
		
	except RuntimeError as e:
		QMessageBox.critical(
			None,
			"Initialization Error",
			str(e)
		)
		sys.exit(1)
	except Exception as e:
		QMessageBox.critical(
			None,
			"Error",
			f"An unexpected error occurred:\n{str(e)}"
		)
		sys.exit(1)


if __name__ == "__main__":
	main()
