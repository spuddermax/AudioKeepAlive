"""System tray icon and menu."""
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal


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
		self._setup_icon()
		self._setup_menu()
		self.tray_icon.setContextMenu(self.menu)
		self.tray_icon.activated.connect(self._on_tray_activated)
	
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
		
		# Show/Hide window action
		self.show_action = QAction("Show Window", self)
		self.show_action.triggered.connect(self.show_window.emit)
		self.menu.addAction(self.show_action)
		
		# Hide window action
		self.hide_action = QAction("Hide Window", self)
		self.hide_action.triggered.connect(self.hide_window.emit)
		self.menu.addAction(self.hide_action)
		
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
			self.show_window.emit()
		# Also handle trigger (single-click on some systems)
		elif reason == QSystemTrayIcon.ActivationReason.Trigger:
			# On some systems, single-click is used instead of double-click
			# Only toggle if window is hidden
			if not self._window_visible:
				self.show_window.emit()
	
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
	
	def update_window_visibility(self, visible: bool):
		"""Update menu actions based on window visibility."""
		self._window_visible = visible
		if visible:
			self.show_action.setText("Hide Window")
		else:
			self.show_action.setText("Show Window")
