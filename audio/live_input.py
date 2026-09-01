"""Capture the default system-output monitor for contextual analysis."""

import subprocess
import threading
from typing import Callable, Optional

import numpy as np

from audio.input import AudioFrame, AudioPlaybackError, PlaybackState


def _run_pactl(command_runner, *arguments: str) -> str:
    try:
        result = command_runner(
            ["pactl", *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AudioPlaybackError(
            "pactl não está instalado ou não está no PATH"
        ) from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or "erro sem detalhes"
        raise AudioPlaybackError(
            f"Falha ao consultar o PipeWire/PulseAudio: {detail}"
        )
    return result.stdout


def discover_default_monitor(command_runner=subprocess.run) -> str:
    """Return the monitor source belonging to the current default sink."""
    sink = _run_pactl(command_runner, "get-default-sink").strip()
    if not sink:
        raise AudioPlaybackError("Não foi possível descobrir o sink padrão")

    expected = f"{sink}.monitor"
    sources = _run_pactl(command_runner, "list", "short", "sources")
    source_names = [
        fields[1]
        for line in sources.splitlines()
        if len(fields := line.split("\t")) > 1
    ]
    if expected not in source_names:
        raise AudioPlaybackError(f"Fonte monitor não encontrada para o sink {sink}")
    return expected


class SystemAudioInput:
    """Sequential mono frames captured from the default output monitor."""

    def __init__(
        self,
        frame_duration: float = 1.0 / 30.0,
        samplerate: int = 48_000,
        command_runner: Callable[..., object] = subprocess.run,
        process_factory: Callable[..., object] = subprocess.Popen,
        thread_factory: Callable[..., object] = threading.Thread,
    ):
        self.frame_duration = frame_duration
        self.samplerate = samplerate
        self.frame_size = max(1, int(samplerate * frame_duration))
        self.source_label = "Áudio do sistema"
        self.state = PlaybackState.STOPPED
        self.error_message: Optional[str] = None

        self._command_runner = command_runner
        self._process_factory = process_factory
        self._thread_factory = thread_factory
        self._process = None
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._pending_samples = np.empty(0, dtype=np.float32)
        self._captured_samples = 0
        self._analysis_cursor = 0

    def play(self) -> None:
        with self._lock:
            if self.state is PlaybackState.PLAYING:
                return

        monitor = discover_default_monitor(self._command_runner)
        command = [
            "parec",
            "--device",
            monitor,
            "--format",
            "float32le",
            "--rate",
            str(self.samplerate),
            "--channels",
            "1",
            "--raw",
        ]
        process = self._process_factory(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        with self._lock:
            self._process = process
            self._pending_samples = np.empty(0, dtype=np.float32)
            self._captured_samples = 0
            self._analysis_cursor = 0
            self._stop_event.clear()
            self.error_message = None
            self.state = PlaybackState.PLAYING
            thread = self._thread_factory(target=self._capture_loop, daemon=True)
            self._thread = thread
        thread.start()

    def _capture_loop(self) -> None:
        remainder = b""
        while not self._stop_event.is_set():
            process = self._process
            chunk = process.stdout.read(4096)
            if not chunk:
                break
            payload = remainder + chunk
            complete_bytes = len(payload) - (len(payload) % 4)
            remainder = payload[complete_bytes:]
            if complete_bytes == 0:
                continue
            samples = np.frombuffer(payload[:complete_bytes], dtype="<f4").copy()
            with self._lock:
                self._pending_samples = np.concatenate(
                    (self._pending_samples, samples)
                )
                self._captured_samples += len(samples)

    def get_position_seconds(self) -> float:
        with self._lock:
            captured_samples = self._captured_samples
        return captured_samples / self.samplerate

    def get_next_frame(self) -> Optional[AudioFrame]:
        with self._lock:
            if len(self._pending_samples) < self.frame_size:
                return None
            start = self._analysis_cursor
            samples = self._pending_samples[: self.frame_size].copy()
            self._pending_samples = self._pending_samples[self.frame_size :]
            self._analysis_cursor += self.frame_size

        return AudioFrame(
            samples=samples,
            timestamp=start / self.samplerate,
            samplerate=self.samplerate,
            frame_index=start // self.frame_size,
        )

    def is_finished(self) -> bool:
        return False

    def stop(self) -> None:
        with self._lock:
            process = self._process
            thread = self._thread
            self._process = None
            self._thread = None
            self._stop_event.set()
            if self.state is not PlaybackState.FAILED:
                self.state = PlaybackState.STOPPED

        if process is not None:
            process.terminate()
            process.wait(timeout=1.0)
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)
