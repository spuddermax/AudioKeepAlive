"""Main application window."""
from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
	QPushButton, QLabel, QSlider, QSpinBox, QMessageBox
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QEvent
from audio_player import AudioPlayer
from settings import Settings


class MainWindow(QMainWindow):
	"""Main application window with all controls."""
	
	# Signals
	playback_started = pyqtSignal()
	playback_stopped = pyqtSignal()
	
	def __init__(self, settings: Settings, tray_icon=None):
		"""Initialize main window."""
		super().__init__()
		self.settings = settings
		self.tray_icon = tray_icon
		self.audio_player = AudioPlayer()
		self.is_playing = False
		self.countdown_seconds = 0
		
		# Timers
		self.play_timer = QTimer(self)
		self.play_timer.timeout.connect(self._on_play_timer)
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
		self.interval_spinbox.setMaximum(3600)
		self.interval_spinbox.setValue(60)
		self.interval_spinbox.setSuffix(" seconds")
		self.interval_spinbox.valueChanged.connect(self._on_interval_changed)
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
		self.freq1_spinbox.valueChanged.connect(self._on_frequency_changed)
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
		self.freq2_spinbox.valueChanged.connect(self._on_frequency_changed)
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
		self.settings.set("volume", self.volume_slider.value())
		self.settings.set("interval", self.interval_spinbox.value())
		self.settings.set("frequency1", self.freq1_spinbox.value())
		self.settings.set("frequency2", self.freq2_spinbox.value())
		self.settings.set_window_geometry(self.saveGeometry())
	
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
		self._update_ui_state()
		self._play_tones()
		
		# Start timer for next play
		interval_ms = self.interval_spinbox.value() * 1000
		self.play_timer.start(interval_ms)
		self.countdown_seconds = self.interval_spinbox.value()
		self._update_countdown()
		
		self.playback_started.emit()
	
	def stop_playback(self):
		"""Stop playing tones."""
		if not self.is_playing:
			return
		
		self.is_playing = False
		self.play_timer.stop()
		self.countdown_seconds = 0
		self._update_ui_state()
		
		self.playback_stopped.emit()
	
	def _play_tones(self):
		"""Play the two tones."""
		volume_percent = self.volume_slider.value()
		volume_sox = self.audio_player.volume_percent_to_sox(volume_percent)
		freq1 = self.freq1_spinbox.value()
		freq2 = self.freq2_spinbox.value()
		
		success = self.audio_player.play_tones(
			frequency1=freq1,
			frequency2=freq2,
			volume=volume_sox
		)
		
		if not success:
			QMessageBox.warning(
				self,
				"Playback Error",
				"Failed to play tones. Please check that SoX is installed and working."
			)
	
	def _on_play_timer(self):
		"""Called when play timer expires."""
		self._play_tones()
		self.countdown_seconds = self.interval_spinbox.value()
	
	def _update_countdown(self):
		"""Update countdown display."""
		if self.is_playing and self.countdown_seconds > 0:
			self.countdown_label.setText(f"Next play in: {self.countdown_seconds} seconds")
			self.countdown_seconds -= 1
		elif not self.is_playing:
			self.countdown_label.setText("Next play in: -- seconds")
	
	def _update_ui_state(self):
		"""Update UI elements based on playback state."""
		if self.is_playing:
			self.status_label.setText("Status: Running")
			self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #2ecc71;")
			self.start_stop_button.setText("⏸ Stop")
		else:
			self.status_label.setText("Status: Stopped")
			self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #e74c3c;")
			self.start_stop_button.setText("▶ Start")
		
		if self.tray_icon:
			self.tray_icon.update_playback_state(self.is_playing)
	
	def _on_volume_changed(self, value: int):
		"""Handle volume slider change."""
		self._update_volume_label(value)
		self._save_settings()
	
	def _update_volume_label(self, value: int):
		"""Update volume label text."""
		self.volume_label.setText(f"{value}%")
	
	def _on_interval_changed(self, value: int):
		"""Handle interval change."""
		if self.is_playing:
			# Restart timer with new interval
			interval_ms = value * 1000
			self.play_timer.start(interval_ms)
			self.countdown_seconds = value
		self._save_settings()
	
	def _on_frequency_changed(self):
		"""Handle frequency change."""
		self._save_settings()
	
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
