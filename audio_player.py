"""Audio playback handler using SoX 'play' (non-blocking, Qt-integrated)."""
import os
import time
import shutil
import signal
import subprocess
from typing import List, Optional

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal


# pgrep pattern used to locate our own SoX 'play' processes for startup cleanup.
_PLAY_PROCESS_PATTERN = "play -n synth"


class AudioPlayer(QObject):
	"""Plays keep-alive tones using SoX 'play' without blocking the GUI thread.

	Playback runs in QProcess instances driven by the Qt event loop, so a hung
	'play' invocation can never freeze the UI. A persistent low-volume stream
	keeps the audio device from suspending between tones, which avoids the
	device-resume race that otherwise leaves 'play' processes wedged.
	"""

	# Emitted with a human-readable message when playback fails.
	playback_error = pyqtSignal(str)

	def __init__(self, parent=None):
		"""Initialize audio player and check for SoX availability."""
		super().__init__(parent)
		self.play_command = self._find_play_command()
		if not self.play_command:
			raise RuntimeError(
				"SoX 'play' command not found. Please install SoX:\n"
				"sudo apt install sox"
			)

		# Clear anything left wedged by a previous run before we start.
		self._cleanup_stuck_processes()

		# Sequential tone-burst playback state.
		self._tone_process: Optional[QProcess] = None
		self._tone_queue: List[List[str]] = []
		self._tone_timeout_ms = 5000
		self._tone_watchdog = QTimer(self)
		self._tone_watchdog.setSingleShot(True)
		self._tone_watchdog.timeout.connect(self._on_tone_timeout)

		# Persistent keep-awake stream (prevents device suspend).
		self._keepalive_process: Optional[QProcess] = None
		self._keepalive_active = False
		self._keepalive_freq = 1
		self._keepalive_vol = 0.0001
		self._keepalive_dur = 86400

	def _find_play_command(self) -> Optional[str]:
		"""Find the play command path."""
		return shutil.which("play")

	# ------------------------------------------------------------------
	# Process cleanup (SIGTERM, then SIGKILL for survivors)
	# ------------------------------------------------------------------
	def _find_stuck_pids(self) -> List[int]:
		"""Return PIDs of SoX 'play' processes matching our command pattern."""
		try:
			result = subprocess.run(
				["pgrep", "-f", _PLAY_PROCESS_PATTERN],
				capture_output=True,
				text=True,
				timeout=2
			)
		except (FileNotFoundError, subprocess.TimeoutExpired):
			return []
		if result.returncode != 0 or not result.stdout.strip():
			return []
		pids = []
		for line in result.stdout.strip().split('\n'):
			try:
				pids.append(int(line))
			except ValueError:
				pass
		return pids

	@staticmethod
	def _signal_pid(pid: int, sig: int) -> None:
		"""Send a signal to a PID, ignoring it if it is already gone."""
		try:
			os.kill(pid, sig)
		except (ProcessLookupError, PermissionError):
			pass

	def _cleanup_stuck_processes(self) -> None:
		"""Kill stuck 'play' processes, escalating SIGTERM -> SIGKILL.

		A 'play' blocked on the audio device frequently ignores SIGTERM, so any
		survivor is force-killed after a short grace period. This runs only at
		startup; runtime hangs are handled by the per-process watchdog. It must
		not be called while our own keep-alive stream is running, since that
		stream matches the same pattern.
		"""
		pids = self._find_stuck_pids()
		if not pids:
			return
		for pid in pids:
			self._signal_pid(pid, signal.SIGTERM)
		# Give them a moment to exit cleanly, then force-kill survivors.
		time.sleep(0.25)
		for pid in set(self._find_stuck_pids()) & set(pids):
			self._signal_pid(pid, signal.SIGKILL)

	def _kill_process(self, proc: QProcess) -> None:
		"""Terminate a QProcess, escalating SIGTERM -> SIGKILL if it lingers."""
		if proc.state() == QProcess.ProcessState.NotRunning:
			return
		# Ignore the finished/error signals this teardown will trigger.
		try:
			proc.finished.disconnect()
		except (TypeError, RuntimeError):
			pass
		try:
			proc.errorOccurred.disconnect()
		except (TypeError, RuntimeError):
			pass
		proc.terminate()  # SIGTERM
		if not proc.waitForFinished(500):
			proc.kill()  # SIGKILL
			proc.waitForFinished(500)

	# ------------------------------------------------------------------
	# Interval tone bursts (two tones played sequentially, non-blocking)
	# ------------------------------------------------------------------
	def play_tones(
		self,
		frequency1: int = 200,
		frequency2: int = 300,
		volume: float = 0.3,
		duration: float = 0.2
	) -> None:
		"""
		Queue two tones to play sequentially without blocking the GUI thread.

		Args:
			frequency1: First tone frequency in Hz (default: 200)
			frequency2: Second tone frequency in Hz (default: 300)
			volume: Volume level 0.0-1.0 (default: 0.3)
			duration: Duration of each tone in seconds (default: 0.2)

		Failures are reported asynchronously via the ``playback_error`` signal.
		"""
		self._tone_queue = [
			self._tone_args(frequency1, volume, duration),
			self._tone_args(frequency2, volume, duration),
		]
		# Watchdog timeout. A tone normally completes in well under a second,
		# but a freshly-spawned 'play' can take several seconds just to get
		# scheduled and connect to the audio server when the system is under
		# heavy load. Use a generous floor so load spikes don't trip the
		# watchdog, while still bounding a genuinely hung process.
		self._tone_timeout_ms = int(max(15.0, duration + 5.0) * 1000)

		# Drop any still-running burst before starting a fresh one.
		if self._tone_process is not None:
			self._tone_watchdog.stop()
			self._kill_process(self._tone_process)
			self._tone_process.deleteLater()
			self._tone_process = None

		self._play_next_tone()

	@staticmethod
	def _tone_args(frequency: int, volume: float, duration: float) -> List[str]:
		"""Build SoX arguments for a single sine tone."""
		return [
			"-n",
			"synth", str(duration),
			"sine", str(frequency),
			"vol", str(volume),
		]

	def _play_next_tone(self) -> None:
		"""Start the next queued tone, chaining the burst via signals."""
		if not self._tone_queue:
			return
		args = self._tone_queue.pop(0)
		proc = QProcess(self)
		proc.setStandardOutputFile(QProcess.nullDevice())
		proc.setStandardErrorFile(QProcess.nullDevice())
		proc.finished.connect(self._on_tone_finished)
		proc.errorOccurred.connect(self._on_tone_error)
		self._tone_process = proc
		proc.start(self.play_command, args)
		self._tone_watchdog.start(self._tone_timeout_ms)

	def _on_tone_finished(self, exit_code, exit_status) -> None:
		"""Advance the burst when a tone exits, or report an abnormal exit."""
		if self.sender() is not self._tone_process:
			return
		self._tone_watchdog.stop()
		proc = self._tone_process
		self._tone_process = None
		proc.deleteLater()

		if (exit_status != QProcess.ExitStatus.NormalExit
				or exit_code != 0):
			self._tone_queue = []
			self.playback_error.emit("A keep-alive tone exited abnormally.")
			return

		self._play_next_tone()

	def _on_tone_error(self, error) -> None:
		"""Report a failure to start or run the 'play' process."""
		if self.sender() is not self._tone_process:
			return
		self._tone_watchdog.stop()
		proc = self._tone_process
		self._tone_process = None
		self._tone_queue = []
		self._kill_process(proc)
		proc.deleteLater()
		self.playback_error.emit("Failed to start the SoX 'play' process.")

	def _on_tone_timeout(self) -> None:
		"""Terminate a tone that ran too long (hung on the audio device)."""
		proc = self._tone_process
		self._tone_process = None
		self._tone_queue = []
		if proc is not None:
			self._kill_process(proc)
			proc.deleteLater()
		self.playback_error.emit(
			"A keep-alive tone timed out (audio device busy) and was terminated."
		)

	# ------------------------------------------------------------------
	# Persistent keep-awake stream (prevents the audio device suspending)
	# ------------------------------------------------------------------
	def start_keepalive(self) -> None:
		"""Start a continuous near-silent stream so the device never suspends."""
		self._keepalive_active = True
		if (self._keepalive_process is not None
				and self._keepalive_process.state()
				!= QProcess.ProcessState.NotRunning):
			return
		self._start_keepalive_process()

	def _start_keepalive_process(self) -> None:
		"""Launch the persistent keep-awake 'play' process."""
		proc = QProcess(self)
		proc.setStandardOutputFile(QProcess.nullDevice())
		proc.setStandardErrorFile(QProcess.nullDevice())
		proc.finished.connect(self._on_keepalive_finished)
		self._keepalive_process = proc
		args = [
			"-n",
			"synth", str(self._keepalive_dur),
			"sine", str(self._keepalive_freq),
			"vol", str(self._keepalive_vol),
		]
		proc.start(self.play_command, args)

	def _on_keepalive_finished(self, exit_code, exit_status) -> None:
		"""Restart the keep-awake stream while it is meant to be active."""
		if self.sender() is not self._keepalive_process:
			return
		self._keepalive_process.deleteLater()
		self._keepalive_process = None
		if self._keepalive_active:
			# Brief delay avoids a hot restart loop if 'play' fails immediately.
			QTimer.singleShot(1000, self._restart_keepalive)

	def _restart_keepalive(self) -> None:
		"""Relaunch the keep-awake stream if it is still wanted and stopped."""
		if self._keepalive_active and self._keepalive_process is None:
			self._start_keepalive_process()

	def stop_keepalive(self) -> None:
		"""Stop the persistent keep-awake stream and force-kill it if needed."""
		self._keepalive_active = False
		proc = self._keepalive_process
		self._keepalive_process = None
		if proc is not None:
			self._kill_process(proc)
			proc.deleteLater()

	def volume_percent_to_sox(self, volume_percent: int) -> float:
		"""
		Convert volume percentage (0-100) to SoX vol parameter (0.0-1.0).

		Args:
			volume_percent: Volume as percentage (0-100)

		Returns:
			Volume as float (0.0-1.0)
		"""
		return max(0.0, min(1.0, volume_percent / 100.0))
