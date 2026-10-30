"""System tray icon and menu."""
from pathlib import Path
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal, Qt

ICON_PATH = Path(__file__).resolve().parent / "icons" / "audiokeepalive.svg"


def app_icon() -> QIcon:
	"""Return the application icon, falling back to a theme icon."""
	icon = QIcon(str(ICON_PATH))
	if icon.isNull() or icon.pixmap(64, 64).isNull():
		icon = QIcon.fromTheme("audio-volume-high")
	if icon.isNull():
		icon = QIcon.fromTheme("application-x-executable")
	return icon


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
		# Set context menu - note: on some systems this can interfere with click detection
		self.tray_icon.setContextMenu(self.menu)
		# Connect activation signal - this handles both single and double clicks
		self.tray_icon.activated.connect(self._on_tray_activated)
	
	def _setup_icon(self):
		"""Setup tray icon, with a greyed-out variant for the stopped state."""
		self._running_icon = app_icon()
		self._stopped_icon = QIcon(
			self._running_icon.pixmap(64, 64, QIcon.Mode.Disabled)
		)
		self._error_icon = QIcon.fromTheme("dialog-warning", self._running_icon)
		self.tray_icon.setIcon(self._stopped_icon)
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
			self.show_window.emit()
		# Also handle trigger (single-click on some systems)
		# On Cinnamon/Linux Mint, single-click may be used
		# Note: If context menu is set, single-click might open menu instead
		elif reason == QSystemTrayIcon.ActivationReason.Trigger:
			if not self._window_visible:
				self.show_window.emit()
	
	def show(self):
		"""Show the tray icon."""
		self.tray_icon.show()
	
	def set_tooltip(self, text: str):
		"""Set tray icon tooltip."""
		self.tray_icon.setToolTip(text)
	
	def update_playback_state(self, is_playing: bool, error: str = None):
		"""Update menu actions and icon based on playback state."""
		if is_playing:
			self.toggle_action.setText("Stop")
			if error:
				self.tray_icon.setIcon(self._error_icon)
				self.set_tooltip(f"Audio Keep-Alive - {error} Retrying...")
			else:
				self.tray_icon.setIcon(self._running_icon)
				self.set_tooltip("Audio Keep-Alive - Running")
		else:
			self.toggle_action.setText("Start")
			self.tray_icon.setIcon(self._stopped_icon)
			self.set_tooltip("Audio Keep-Alive - Stopped")
	
	def _toggle_window_visibility(self):
		"""Toggle window visibility based on current state."""
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
