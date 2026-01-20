"""Audio playback handler using SoX play command."""
import subprocess
import shutil
import os
import signal
from typing import Optional


class AudioPlayer:
	"""Handles audio playback using SoX play command."""
	
	def __init__(self):
		"""Initialize audio player and check for SoX availability."""
		self.play_command = self._find_play_command()
		if not self.play_command:
			raise RuntimeError(
				"SoX 'play' command not found. Please install SoX:\n"
				"sudo apt install sox"
			)
		self._cleanup_stuck_processes()
	
	def _cleanup_stuck_processes(self):
		"""Kill any stuck play processes from previous runs."""
		try:
			# Find play processes that might be stuck
			result = subprocess.run(
				["pgrep", "-f", "play -n synth"],
				capture_output=True,
				text=True,
				timeout=2
			)
			if result.returncode == 0 and result.stdout.strip():
				pids = result.stdout.strip().split('\n')
				for pid in pids:
					try:
						pid_int = int(pid)
						# Try SIGTERM first, then SIGKILL if needed
						os.kill(pid_int, signal.SIGTERM)
					except (ValueError, ProcessLookupError, PermissionError):
						pass
		except (FileNotFoundError, subprocess.TimeoutExpired):
			# pgrep not available or timed out, skip cleanup
			pass
	
	def _find_play_command(self) -> Optional[str]:
		"""Find the play command path."""
		play_path = shutil.which("play")
		return play_path
	
	def play_tones(
		self,
		frequency1: int = 200,
		frequency2: int = 300,
		volume: float = 0.3,
		duration: float = 0.2
	) -> bool:
		"""
		Play two tones sequentially.
		
		Args:
			frequency1: First tone frequency in Hz (default: 200)
			frequency2: Second tone frequency in Hz (default: 300)
			volume: Volume level 0.0-1.0 (default: 0.3)
			duration: Duration of each tone in seconds (default: 0.2)
		
		Returns:
			True if successful, False otherwise
		"""
		try:
			# Play first tone
			cmd1 = [
				self.play_command,
				"-n",
				"synth", str(duration),
				"sine", str(frequency1),
				"vol", str(volume)
			]
			# Use run with timeout and start_new_session to create a new process group
			# This allows us to kill the entire process tree if it hangs
			result1 = subprocess.run(
				cmd1,
				stdout=subprocess.DEVNULL,
				stderr=subprocess.DEVNULL,
				timeout=max(5, duration + 2),  # Timeout slightly longer than duration
				start_new_session=True  # Create new process group
			)
			
			if result1.returncode != 0:
				return False
			
			# Play second tone
			cmd2 = [
				self.play_command,
				"-n",
				"synth", str(duration),
				"sine", str(frequency2),
				"vol", str(volume)
			]
			result2 = subprocess.run(
				cmd2,
				stdout=subprocess.DEVNULL,
				stderr=subprocess.DEVNULL,
				timeout=max(5, duration + 2),
				start_new_session=True
			)
			
			return result2.returncode == 0
			
		except subprocess.TimeoutExpired:
			# Process timed out - subprocess.run should have killed it, but clean up anyway
			self._cleanup_stuck_processes()
			return False
		except (FileNotFoundError, OSError) as e:
			print(f"Error playing tones: {e}")
			return False
	
	def volume_percent_to_sox(self, volume_percent: int) -> float:
		"""
		Convert volume percentage (0-100) to SoX vol parameter (0.0-1.0).
		
		Args:
			volume_percent: Volume as percentage (0-100)
		
		Returns:
			Volume as float (0.0-1.0)
		"""
		return max(0.0, min(1.0, volume_percent / 100.0))
