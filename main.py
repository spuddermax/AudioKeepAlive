#!/usr/bin/env python3
"""Audio Keep-Alive Desktop Application."""
import sys
from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon
from PyQt6.QtCore import Qt
from main_window import MainWindow
from tray_icon import TrayIcon
from settings import Settings


def main():
	"""Main application entry point."""
	# Enable high DPI scaling
	QApplication.setHighDpiScaleFactorRoundingPolicy(
		Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
	)
	
	app = QApplication(sys.argv)
	app.setQuitOnLastWindowClosed(False)
	
	# Check if system tray is available
	if not QSystemTrayIcon.isSystemTrayAvailable():
		QMessageBox.critical(
			None,
			"System Tray",
			"System tray is not available on this system."
		)
		sys.exit(1)
	
	try:
		# Initialize components
		settings = Settings()
		tray_icon = TrayIcon()
		main_window = MainWindow(settings, tray_icon)
		
		# Connect signals
		tray_icon.show_window.connect(main_window.show)
		tray_icon.show_window.connect(main_window.raise_)
		tray_icon.show_window.connect(main_window.activateWindow)
		tray_icon.hide_window.connect(main_window.hide)
		tray_icon.toggle_playback.connect(main_window._toggle_playback)
		tray_icon.quit_requested.connect(app.quit)
		
		main_window.playback_started.connect(
			lambda: tray_icon.update_playback_state(True)
		)
		main_window.playback_stopped.connect(
			lambda: tray_icon.update_playback_state(False)
		)
		
		# Show tray icon
		tray_icon.show()
		
		# Show main window
		main_window.show()
		
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
