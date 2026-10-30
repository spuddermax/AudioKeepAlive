"""Audio playback handler: one continuous SoX 'play' stream."""
import array
import logging
import math
import os
import shutil
import signal
import subprocess
import time
import wave
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal

logger = logging.getLogger(__name__)

SAMPLE_RATE = 48000
TONE_SECONDS = 0.2
FADE_SECONDS = 0.005  # Softens tone edges so they don't click.

CYCLE_FILE = Path.home() / ".cache" / "audiokeepalive" / "cycle.wav"

# pgrep pattern used to locate a stream orphaned by a previous run. Anchored to
# the start of the command line so it cannot match unrelated processes (shells,
# editors, pgrep itself) that merely mention the command.
_PLAY_PROCESS_PATTERN = r"^\S*play .*audiokeepalive/cycle\.wav repeat"

STALL_SECONDS = 15  # No progress from 'play' for this long means it is stuck.
STALL_CHECK_MS = 5000
HEALTHY_SECONDS = 30  # A stream that lasted this long resets the retry delay.
MAX_RETRY_SECONDS = 30


class AudioPlayer(QObject):
	"""Plays keep-alive tones through one long-lived SoX 'play' process.

	One interval (tone, tone, silence) is rendered to a WAV file and looped
	forever, so the audio connection is made once rather than for every tone
	and the audio clock keeps the timing. Any exit is unexpected: the stream is
	restarted with a growing delay until it runs again.
	"""

	# Emitted with a human-readable message when the stream fails.
	playback_error = pyqtSignal(str)
	# Emitted when the stream is playing again after a failure.
	playback_recovered = pyqtSignal()

	def __init__(self, parent=None):
		"""Initialize audio player and check for SoX availability."""
		super().__init__(parent)
		self.play_command = self._find_play_command()
		if not self.play_command:
			raise RuntimeError(
				"SoX 'play' command not found. Please install SoX:\n"
				"sudo apt install sox"
			)

		# Clear a stream orphaned by a previous run before we start.
		self._cleanup_stuck_processes()

		self._frequency1 = 200
		self._frequency2 = 300
		self._volume_percent = 30
		self._interval = 60

		self._active = False
		self._failing = False
		self._stream: Optional[QProcess] = None
		self._stream_output = ""
		self._stream_started = 0.0
		self._last_progress = 0.0
		self._cycle_origin: Optional[float] = None

		self._retry_seconds = 1
		self._retry_timer = QTimer(self)
		self._retry_timer.setSingleShot(True)
		self._retry_timer.timeout.connect(self._start_stream)

		self._stall_timer = QTimer(self)
		self._stall_timer.timeout.connect(self._check_for_stall)

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
		"""Kill orphaned 'play' processes, escalating SIGTERM -> SIGKILL.

		This runs only at startup, before our own stream exists, since that
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
		# Ignore the signals this teardown will trigger.
		for sig in (
			proc.finished,
			proc.errorOccurred,
			proc.readyReadStandardError,
		):
			try:
				sig.disconnect()
			except (TypeError, RuntimeError):
				pass
		if proc.state() == QProcess.ProcessState.NotRunning:
			return
		proc.terminate()  # SIGTERM
		if not proc.waitForFinished(500):
			proc.kill()  # SIGKILL
			proc.waitForFinished(500)

	# ------------------------------------------------------------------
	# Cycle rendering
	# ------------------------------------------------------------------
	def _tone_samples(self, frequency: int) -> array.array:
		"""Build one faded sine tone as signed 16-bit samples."""
		amplitude = 32767 * max(0.0, min(1.0, self._volume_percent / 100.0))
		count = int(SAMPLE_RATE * TONE_SECONDS)
		fade = int(SAMPLE_RATE * FADE_SECONDS)
		samples = array.array("h")
		for i in range(count):
			envelope = min(1.0, i / fade, (count - 1 - i) / fade)
			phase = 2 * math.pi * frequency * i / SAMPLE_RATE
			samples.append(int(amplitude * envelope * math.sin(phase)))
		return samples

	def _render_cycle(self) -> None:
		"""Write one interval (tone, tone, silence) to the cycle file."""
		tones = self._tone_samples(self._frequency1)
		tones.extend(self._tone_samples(self._frequency2))
		silent_frames = max(0, self._interval * SAMPLE_RATE - len(tones))

		CYCLE_FILE.parent.mkdir(parents=True, exist_ok=True)
		temp_file = CYCLE_FILE.with_suffix(".tmp")
		with wave.open(str(temp_file), "wb") as wav:
			wav.setnchannels(1)
			wav.setsampwidth(2)
			wav.setframerate(SAMPLE_RATE)
			wav.writeframes(tones.tobytes())
			second_of_silence = bytes(2 * SAMPLE_RATE)
			for _ in range(silent_frames // SAMPLE_RATE):
				wav.writeframes(second_of_silence)
			wav.writeframes(bytes(2 * (silent_frames % SAMPLE_RATE)))
		os.replace(temp_file, CYCLE_FILE)

	# ------------------------------------------------------------------
	# Stream lifecycle
	# ------------------------------------------------------------------
	def configure(
		self,
		frequency1: int,
		frequency2: int,
		volume_percent: int,
		interval: int
	) -> None:
		"""
		Set the cycle, restarting the stream if it changed while active.

		Args:
			frequency1: First tone frequency in Hz
			frequency2: Second tone frequency in Hz
			volume_percent: Volume as percentage (0-100)
			interval: Seconds between the start of each pair of tones
		"""
		changed = (frequency1, frequency2, volume_percent, interval) != (
			self._frequency1,
			self._frequency2,
			self._volume_percent,
			self._interval,
		)
		self._frequency1 = frequency1
		self._frequency2 = frequency2
		self._volume_percent = volume_percent
		self._interval = interval
		if changed and self._active:
			self._stop_stream()
			self._start_stream()

	def start(self) -> None:
		"""Start the continuous stream."""
		if self._active:
			return
		self._active = True
		self._retry_seconds = 1
		self._stall_timer.start(STALL_CHECK_MS)
		self._start_stream()

	def stop(self) -> None:
		"""Stop the continuous stream and force-kill it if needed."""
		self._active = False
		self._failing = False
		self._stall_timer.stop()
		self._stop_stream()

	def seconds_until_next_tone(self) -> Optional[int]:
		"""Return the seconds until the next tones, or None if not playing."""
		if self._cycle_origin is None:
			return None
		elapsed = time.monotonic() - self._cycle_origin
		return math.ceil(self._interval - elapsed % self._interval)

	def _start_stream(self) -> None:
		"""Render the cycle and launch the looping 'play' process."""
		self._retry_timer.stop()
		if not self._active:
			return
		try:
			self._render_cycle()
		except OSError as e:
			self._on_stream_failed(f"Could not write the tone file: {e}")
			return

		proc = QProcess(self)
		proc.setStandardOutputFile(QProcess.nullDevice())
		proc.readyReadStandardError.connect(self._on_stream_output)
		proc.finished.connect(self._on_stream_finished)
		proc.errorOccurred.connect(self._on_stream_error)
		self._stream = proc
		self._stream_output = ""
		self._stream_started = time.monotonic()
		self._last_progress = self._stream_started
		self._cycle_origin = None
		logger.info(
			"Starting stream: %s Hz, %s Hz, volume %s%%, every %s seconds",
			self._frequency1,
			self._frequency2,
			self._volume_percent,
			self._interval
		)
		# -S makes 'play' report progress, which is how a stall is detected.
		proc.start(self.play_command, ["-S", str(CYCLE_FILE), "repeat", "-"])

	def _stop_stream(self) -> None:
		"""Tear down the stream and any pending restart."""
		self._retry_timer.stop()
		self._cycle_origin = None
		proc = self._stream
		self._stream = None
		if proc is not None:
			self._kill_process(proc)
			proc.deleteLater()

	def _on_stream_output(self) -> None:
		"""Track progress from 'play' and log anything else it says."""
		if self.sender() is not self._stream:
			return
		data = bytes(self._stream.readAllStandardError())
		text = self._stream_output + data.decode(errors="replace")
		lines = text.replace("\r", "\n").split("\n")
		self._stream_output = lines.pop()
		for line in lines:
			line = line.strip()
			if line.startswith("In:"):
				self._on_stream_progress()
			elif line:
				logger.info("play: %s", line)

	def _on_stream_progress(self) -> None:
		"""Note that audio is flowing, clearing any earlier failure."""
		self._last_progress = time.monotonic()
		if self._cycle_origin is None:
			self._cycle_origin = self._last_progress
		if self._failing:
			self._failing = False
			logger.info("Stream recovered")
			self.playback_recovered.emit()

	def _on_stream_finished(self, exit_code, exit_status) -> None:
		"""Handle the stream exiting, which it should never do by itself."""
		if self.sender() is not self._stream:
			return
		self._on_stream_failed(f"The audio stream exited (code {exit_code}).")

	def _on_stream_error(self, error) -> None:
		"""Handle a failure to launch 'play'."""
		if self.sender() is not self._stream:
			return
		if error == QProcess.ProcessError.FailedToStart:
			self._on_stream_failed("Failed to start the SoX 'play' process.")

	def _check_for_stall(self) -> None:
		"""Replace a stream that is still running but no longer progressing."""
		if self._stream is None:
			return
		if time.monotonic() - self._last_progress > STALL_SECONDS:
			self._on_stream_failed("The audio stream stalled.")

	def _on_stream_failed(self, message: str) -> None:
		"""Clear a failed stream and schedule a restart with backoff."""
		if time.monotonic() - self._stream_started >= HEALTHY_SECONDS:
			self._retry_seconds = 1
		delay = self._retry_seconds
		self._retry_seconds = min(delay * 2, MAX_RETRY_SECONDS)
		self._stop_stream()
		logger.warning("%s Retrying in %s seconds.", message, delay)
		self._retry_timer.start(delay * 1000)
		if not self._failing:
			self._failing = True
			self.playback_error.emit(message)
