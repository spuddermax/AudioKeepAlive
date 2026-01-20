"""Settings management for Audio Keep-Alive application."""
import json
from pathlib import Path
from typing import Any, Optional


class Settings:
	"""Manages application settings persistence."""
	
	def __init__(self):
		"""Initialize settings with default values."""
		self.config_dir = Path.home() / ".config" / "audiokeepalive"
		self.config_file = self.config_dir / "settings.json"
		
		# Default settings
		self.defaults = {
			"volume": 30,  # 0-100, maps to SoX vol 0.0-1.0
			"interval": 60,  # seconds
			"frequency1": 200,  # Hz
			"frequency2": 300,  # Hz
			"window_geometry": None,  # Will store window position/size
		}
		
		self.settings = self.defaults.copy()
		self.load()
	
	def load(self) -> None:
		"""Load settings from JSON file."""
		if self.config_file.exists():
			try:
				with open(self.config_file, 'r') as f:
					loaded = json.load(f)
					self.settings.update(loaded)
			except (json.JSONDecodeError, IOError) as e:
				print(f"Error loading settings: {e}")
				self.settings = self.defaults.copy()
	
	def save(self) -> None:
		"""Save settings to JSON file."""
		try:
			self.config_dir.mkdir(parents=True, exist_ok=True)
			with open(self.config_file, 'w') as f:
				json.dump(self.settings, f, indent=2)
		except IOError as e:
			print(f"Error saving settings: {e}")
	
	def get(self, key: str, default: Any = None) -> Any:
		"""Get a setting value."""
		return self.settings.get(key, default)
	
	def set(self, key: str, value: Any) -> None:
		"""Set a setting value and save."""
		self.settings[key] = value
		self.save()
	
	def get_window_geometry(self) -> Optional[bytes]:
		"""Get saved window geometry."""
		geom = self.settings.get("window_geometry")
		if geom:
			return bytes.fromhex(geom)
		return None
	
	def set_window_geometry(self, geometry) -> None:
		"""Save window geometry.
		
		Args:
			geometry: QByteArray or bytes object from saveGeometry()
		"""
		# Convert QByteArray to bytes (works for both QByteArray and bytes)
		geom_bytes = bytes(geometry)
		self.set("window_geometry", geom_bytes.hex())
