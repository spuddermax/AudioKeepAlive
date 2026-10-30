"""Main application window."""
from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
	QPushButton, QLabel, QSlider, QSpinBox
)
from PyQt6.QtCore import QTimer, Qt, QEvent
from audio_player import AudioPlayer
from settings import Settings


# Longest allowed interval. The looped file grows with the interval, and a
# soundbar's auto-off timer is far longer than the gap this leaves.
MAX_INTERVAL_SECONDS = 600

# Controls can fire many changes per second; wait for them to settle.
APPLY_DELAY_MS = 400


class MainWindow(QMainWindow):
	"""Main application window with all controls."""
	
	def __init__(self, settings: Settings, tray_icon=None):
		"""Initialize main window."""
		super().__init__()
		self.settings = settings
		self.tray_icon = tray_icon
		self.audio_player = AudioPlayer(self)
		self.audio_player.playback_error.connect(self._on_playback_error)
		self.audio_player.playback_recovered.connect(self._on_playback_recovered)
		self.is_playing = False
		self.audio_error = None
		
		# Timers
		self.apply_timer = QTimer(self)
		self.apply_timer.setSingleShot(True)
		self.apply_timer.timeout.connect(self._apply_settings)
		self.countdown_timer = QTimer(self)
		self.countdown_timer.timeout.connect(self._update_countdown)
		self.countdown_timer.start(1000)  # Update every second
		
		self._init_ui()
		self._load_settings()
		
		# Auto-start playback
		self.start_playback()
	
	def _init_ui(self):
		"""Initialize UI components."""
		self.setWindowTitle("Audio Keep-Alive")
		self.setMinimumWidth(350)
		self.setMinimumHeight(300)
		
		# Central widget
		central_widget = QWidget()
		self.setCentralWidget(central_widget)
		layout = QVBoxLayout(central_widget)
		layout.setSpacing(15)
		layout.setContentsMargins(20, 20, 20, 20)
		
		# Status section
		status_layout = QVBoxLayout()
		self.status_label = QLabel("Status: Stopped")
		self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
		status_layout.addWidget(self.status_label)
		
		self.countdown_label = QLabel("Next play in: -- seconds")
		self.countdown_label.setStyleSheet("color: #666;")
		status_layout.addWidget(self.countdown_label)
		layout.addLayout(status_layout)
		
		# Control buttons
		button_layout = QHBoxLayout()
		self.start_stop_button = QPushButton("▶ Stop")
		self.start_stop_button.setMinimumHeight(40)
		self.start_stop_button.clicked.connect(self._toggle_playback)
		button_layout.addWidget(self.start_stop_button)
		
		self.minimize_button = QPushButton("Minimize to Tray")
		self.minimize_button.clicked.connect(self._minimize_to_tray)
		button_layout.addWidget(self.minimize_button)
		layout.addLayout(button_layout)
		
		# Volume control
		volume_layout = QHBoxLayout()
		volume_label = QLabel("Volume:")
		volume_layout.addWidget(volume_label)
		
		self.volume_slider = QSlider(Qt.Orientation.Horizontal)
		self.volume_slider.setMinimum(0)
		self.volume_slider.setMaximum(100)
		self.volume_slider.setValue(30)
		self.volume_slider.valueChanged.connect(self._on_volume_changed)
		volume_layout.addWidget(self.volume_slider)
		
		self.volume_label = QLabel("30%")
		self.volume_label.setMinimumWidth(50)
		volume_layout.addWidget(self.volume_label)
		layout.addLayout(volume_layout)
		
		# Interval control
		interval_layout = QHBoxLayout()
		interval_label = QLabel("Interval:")
		interval_layout.addWidget(interval_label)
		
		self.interval_spinbox = QSpinBox()
		self.interval_spinbox.setMinimum(1)
		self.interval_spinbox.setMaximum(MAX_INTERVAL_SECONDS)
		self.interval_spinbox.setValue(60)
		self.interval_spinbox.setSuffix(" seconds")
		self.interval_spinbox.valueChanged.connect(self._on_setting_changed)
		interval_layout.addWidget(self.interval_spinbox)
		layout.addLayout(interval_layout)
		
		# Frequency controls
		freq1_layout = QHBoxLayout()
		freq1_label = QLabel("Tone 1 Frequency:")
		freq1_layout.addWidget(freq1_label)
		
		self.freq1_spinbox = QSpinBox()
		self.freq1_spinbox.setMinimum(20)
		self.freq1_spinbox.setMaximum(20000)
		self.freq1_spinbox.setValue(200)
		self.freq1_spinbox.setSuffix(" Hz")
		self.freq1_spinbox.valueChanged.connect(self._on_setting_changed)
		freq1_layout.addWidget(self.freq1_spinbox)
		layout.addLayout(freq1_layout)
		
		freq2_layout = QHBoxLayout()
		freq2_label = QLabel("Tone 2 Frequency:")
		freq2_layout.addWidget(freq2_label)
		
		self.freq2_spinbox = QSpinBox()
		self.freq2_spinbox.setMinimum(20)
		self.freq2_spinbox.setMaximum(20000)
		self.freq2_spinbox.setValue(300)
		self.freq2_spinbox.setSuffix(" Hz")
		self.freq2_spinbox.valueChanged.connect(self._on_setting_changed)
		freq2_layout.addWidget(self.freq2_spinbox)
		layout.addLayout(freq2_layout)
		
		# Add stretch at bottom
		layout.addStretch()
	
	def _load_settings(self):
		"""Load settings into UI."""
		volume = self.settings.get("volume", 30)
		self.volume_slider.setValue(volume)
		self._update_volume_label(volume)
		
		interval = self.settings.get("interval", 60)
		self.interval_spinbox.setValue(interval)
		
		freq1 = self.settings.get("frequency1", 200)
		self.freq1_spinbox.setValue(freq1)
		
		freq2 = self.settings.get("frequency2", 300)
		self.freq2_spinbox.setValue(freq2)
		
		# Restore window geometry
		geometry = self.settings.get_window_geometry()
		if geometry:
			self.restoreGeometry(geometry)
	
	def _save_settings(self):
		"""Save current UI state to settings."""
		self.settings.update({
			"volume": self.volume_slider.value(),
			"interval": self.interval_spinbox.value(),
			"frequency1": self.freq1_spinbox.value(),
			"frequency2": self.freq2_spinbox.value(),
			"window_geometry": bytes(self.saveGeometry()).hex(),
		})
	
	def _configure_player(self):
		"""Pass the current controls to the audio player."""
		self.audio_player.configure(
			self.freq1_spinbox.value(),
			self.freq2_spinbox.value(),
			self.volume_slider.value(),
			self.interval_spinbox.value()
		)
	
	def _apply_settings(self):
		"""Save settings and apply them to the audio stream."""
		self._save_settings()
		self._configure_player()
	
	def _toggle_playback(self):
		"""Toggle playback on/off."""
		if self.is_playing:
			self.stop_playback()
		else:
			self.start_playback()
	
	def start_playback(self):
		"""Start playing tones."""
		if self.is_playing:
			return
		
		self.is_playing = True
		self._configure_player()
		self.audio_player.start()
		self._update_ui_state()
		self._update_countdown()
	
	def stop_playback(self):
		"""Stop playing tones."""
		if not self.is_playing:
			return
		
		self.is_playing = False
		self.audio_player.stop()
		self.audio_error = None
		self._update_ui_state()
		self._update_countdown()
	
	def shutdown(self):
		"""Save settings and stop the stream as the application exits."""
		self._save_settings()
		self.audio_player.stop()
	
	def _on_playback_error(self, message: str):
		"""Show a playback failure; the player keeps retrying on its own."""
		self.audio_error = message
		self._update_ui_state()
	
	def _on_playback_recovered(self):
		"""Clear the failure shown once the stream is playing again."""
		self.audio_error = None
		self._update_ui_state()
	
	def _update_countdown(self):
		"""Update countdown display."""
		seconds = self.audio_player.seconds_until_next_tone()
		if seconds is None:
			self.countdown_label.setText("Next play in: -- seconds")
		else:
			self.countdown_label.setText(f"Next play in: {seconds} seconds")
	
	def _update_ui_state(self):
		"""Update UI elements based on playback state."""
		if self.is_playing:
			if self.audio_error:
				self.status_label.setText("Status: Running (audio error)")
				self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #e67e22;")
			else:
				self.status_label.setText("Status: Running")
				self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #2ecc71;")
			self.start_stop_button.setText("⏸ Stop")
		else:
			self.status_label.setText("Status: Stopped")
			self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #e74c3c;")
			self.start_stop_button.setText("▶ Start")
		
		if self.tray_icon:
			self.tray_icon.update_playback_state(self.is_playing, self.audio_error)
	
	def _on_volume_changed(self, value: int):
		"""Handle volume slider change."""
		self._update_volume_label(value)
		self._on_setting_changed()
	
	def _update_volume_label(self, value: int):
		"""Update volume label text."""
		self.volume_label.setText(f"{value}%")
	
	def _on_setting_changed(self):
		"""Apply a changed control once it has settled."""
		self.apply_timer.start(APPLY_DELAY_MS)
	
	def show_and_raise(self):
		"""Show the window, restoring it if needed, and bring it to the front."""
		self.setWindowState(Qt.WindowState.WindowNoState)
		self.show()
		self.raise_()
		self.activateWindow()
		if self.tray_icon:
			self.tray_icon.update_window_visibility(True)
	
	def _minimize_to_tray(self):
		"""Minimize window to system tray."""
		if self.tray_icon:
			self.hide()
			self.tray_icon.update_window_visibility(False)
		else:
			self.showMinimized()
	
	def changeEvent(self, event):
		"""Handle window state changes (e.g., minimize)."""
		if event.type() == QEvent.Type.WindowStateChange:
			# Check if window was minimized via system minimize button
			if self.isMinimized():
				# Hide to tray instead of minimizing normally
				if self.tray_icon and self.tray_icon.tray_icon.isVisible():
					# Use a timer to hide after the minimize event completes
					QTimer.singleShot(0, self._hide_to_tray)
		super().changeEvent(event)
	
	def _hide_to_tray(self):
		"""Hide window to tray (called after minimize event)."""
		if self.tray_icon and self.tray_icon.tray_icon.isVisible():
			# Clear minimized state before hiding
			self.setWindowState(Qt.WindowState.WindowNoState)
			# Hide the window
			self.hide()
			# Update tray icon state immediately
			self.tray_icon.update_window_visibility(False)
	
	def closeEvent(self, event):
		"""Handle window close event."""
		# Save settings and geometry
		self._save_settings()
		
		# Hide instead of closing if tray icon is available
		if self.tray_icon and self.tray_icon.tray_icon.isVisible():
			event.ignore()
			self.hide()
			self.tray_icon.update_window_visibility(False)
		else:
			event.accept()
