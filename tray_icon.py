"""System tray icon and menu."""
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal, Qt


class TrayIcon(QObject):
	"""System tray icon with context menu."""
	
	# Signals
	show_window = pyqtSignal()
	hide_window = pyqtSignal()
	toggle_playback = pyqtSignal()
	quit_requested = pyqtSignal()
	
	def __init__(self, parent=None):
		"""Initialize system tray icon."""
		super().__init__(parent)
		self.tray_icon = QSystemTrayIcon(parent)
		self._window_visible = True
		self._main_window = None  # Will be set by main application
		self._setup_icon()
		self._setup_menu()
		# Set context menu - note: on some systems this can interfere with click detection
		self.tray_icon.setContextMenu(self.menu)
		# Connect activation signal - this handles both single and double clicks
		self.tray_icon.activated.connect(self._on_tray_activated)
	
	def set_main_window(self, window):
		"""Set reference to main window for direct access."""
		self._main_window = window
	
	def _setup_icon(self):
		"""Setup tray icon (using default Qt icon for now)."""
		# Use a simple icon - in a real app you'd load a custom icon
		icon = QIcon.fromTheme("audio-volume-high")
		if icon.isNull():
			# Fallback to a simple icon
			icon = QIcon.fromTheme("application-x-executable")
		self.tray_icon.setIcon(icon)
		self.tray_icon.setToolTip("Audio Keep-Alive")
	
	def _setup_menu(self):
		"""Setup context menu."""
		self.menu = QMenu()
		
		# Show/Hide window action (toggles based on visibility)
		self.show_action = QAction("Show Window", self)
		self.show_action.triggered.connect(self._toggle_window_visibility)
		self.menu.addAction(self.show_action)
		
		self.menu.addSeparator()
		
		# Start/Stop action
		self.toggle_action = QAction("Start", self)
		self.toggle_action.triggered.connect(self.toggle_playback.emit)
		self.menu.addAction(self.toggle_action)
		
		self.menu.addSeparator()
		
		# Quit action
		quit_action = QAction("Quit", self)
		quit_action.triggered.connect(self.quit_requested.emit)
		self.menu.addAction(quit_action)
	
	def _on_tray_activated(self, reason):
		"""Handle tray icon activation (e.g., double-click)."""
		# Handle double-click to restore window
		if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
			# Always restore/show the window on double-click
			# Try direct method first if available, then emit signal
			if self._main_window:
				self._restore_window_direct()
			else:
				self.show_window.emit()
		# Also handle trigger (single-click on some systems)
		# On Cinnamon/Linux Mint, single-click may be used
		# Note: If context menu is set, single-click might open menu instead
		elif reason == QSystemTrayIcon.ActivationReason.Trigger:
			# Restore window on single-click if it's hidden
			# This is a fallback for systems that use single-click
			if not self._window_visible:
				if self._main_window:
					self._restore_window_direct()
				else:
					self.show_window.emit()
	
	def _restore_window_direct(self):
		"""Directly restore the main window (bypasses signals)."""
		if not self._main_window:
			return
		
		# Restore from minimized state
		if self._main_window.isMinimized():
			self._main_window.showNormal()
		
		# Show the window
		self._main_window.setVisible(True)
		self._main_window.show()
		
		# Clear minimized state
		self._main_window.setWindowState(Qt.WindowState.WindowNoState)
		
		# Bring to front
		self._main_window.raise_()
		self._main_window.activateWindow()
		self._main_window.setFocus()
		
		# Update visibility state
		self.update_window_visibility(True)
	
	def show(self):
		"""Show the tray icon."""
		self.tray_icon.show()
	
	def set_tooltip(self, text: str):
		"""Set tray icon tooltip."""
		self.tray_icon.setToolTip(text)
	
	def update_playback_state(self, is_playing: bool):
		"""Update menu actions based on playback state."""
		if is_playing:
			self.toggle_action.setText("Stop")
			self.set_tooltip("Audio Keep-Alive - Running")
		else:
			self.toggle_action.setText("Start")
			self.set_tooltip("Audio Keep-Alive - Stopped")
	
	def _toggle_window_visibility(self):
		"""Toggle window visibility based on current state."""
		# Check actual window state if we have a reference
		if self._main_window:
			# If window is hidden or minimized, show it
			if self._main_window.isHidden() or self._main_window.isMinimized():
				self.show_window.emit()
			else:
				self.hide_window.emit()
		else:
			# Fallback to tracked state
			if self._window_visible:
				self.hide_window.emit()
			else:
				self.show_window.emit()
	
	def update_window_visibility(self, visible: bool):
		"""Update menu actions based on window visibility."""
		self._window_visible = visible
		if visible:
			self.show_action.setText("Hide Window")
		else:
			self.show_action.setText("Show Window")
