"""Capture the default system-output monitor for contextual analysis."""

from collections import deque
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
        self._stderr_thread = None
        self._stop_event = threading.Event()
        self._stderr_finished = threading.Event()
        self._lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()
        self._sample_chunks = deque()
        self._available_samples = 0
        self._captured_samples = 0
        self._analysis_cursor = 0

    def play(self) -> None:
        with self._lifecycle_lock:
            self._play()

    def _play(self) -> None:
        with self._lock:
            if self.state is PlaybackState.PLAYING:
                return
            has_previous_session = any(
                resource is not None
                for resource in (
                    self._process,
                    self._thread,
                    self._stderr_thread,
                )
            )
        if has_previous_session:
            self._stop()

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
        try:
            process = self._process_factory(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
        except FileNotFoundError as exc:
            message = "parec não está instalado ou não está no PATH"
            with self._lock:
                self.state = PlaybackState.FAILED
                self.error_message = message
            raise AudioPlaybackError(message) from exc
        except Exception as exc:
            message = f"Falha ao iniciar a captura do áudio do sistema: {exc}"
            with self._lock:
                self.state = PlaybackState.FAILED
                self.error_message = message
            raise AudioPlaybackError(message) from exc
        thread = None
        stderr_thread = None
        try:
            with self._lock:
                self._process = process
                self._sample_chunks.clear()
                self._available_samples = 0
                self._captured_samples = 0
                self._analysis_cursor = 0
                self._stop_event.clear()
                self._stderr_finished.clear()
                self._stderr_tail = bytearray()
                self.error_message = None
                self.state = PlaybackState.PLAYING
                thread = self._thread_factory(target=self._capture_loop, daemon=True)
                stderr_thread = self._thread_factory(
                    target=self._stderr_loop, daemon=True
                )
                self._thread = thread
                self._stderr_thread = stderr_thread
            stderr_thread.start()
            thread.start()
        except Exception as exc:
            message = f"Falha ao iniciar a captura do áudio do sistema: {exc}"
            with self._lock:
                self._stop_event.set()
                self._process = None
                self._thread = None
                self._stderr_thread = None
                self.error_message = message
                self.state = PlaybackState.FAILED
            self._cleanup_resources(process, thread, stderr_thread)
            raise AudioPlaybackError(message) from exc

    def _capture_loop(self) -> None:
        remainder = b""
        process = self._process
        try:
            while not self._stop_event.is_set():
                chunk = process.stdout.read(4096)
                if not chunk:
                    if not self._stop_event.is_set():
                        self._record_unexpected_exit(process)
                    break
                payload = remainder + chunk
                complete_bytes = len(payload) - (len(payload) % 4)
                remainder = payload[complete_bytes:]
                if complete_bytes == 0:
                    continue
                samples = np.frombuffer(payload[:complete_bytes], dtype="<f4").copy()
                with self._lock:
                    self._sample_chunks.append(samples)
                    self._available_samples += len(samples)
                    self._captured_samples += len(samples)
        except Exception as exc:
            if not self._stop_event.is_set():
                with self._lock:
                    self.error_message = f"Falha durante a captura de áudio: {exc}"
                    self.state = PlaybackState.FAILED

    def _stderr_loop(self) -> None:
        process = self._process
        try:
            while True:
                chunk = process.stderr.read(1024)
                if not chunk:
                    break
                with self._lock:
                    self._stderr_tail.extend(chunk)
                    if len(self._stderr_tail) > 8192:
                        del self._stderr_tail[:-8192]
        finally:
            self._stderr_finished.set()

    def _record_unexpected_exit(self, process) -> None:
        returncode = process.poll()
        self._stderr_finished.wait(timeout=0.05)
        if returncode is None:
            returncode = process.poll()
        with self._lock:
            detail = bytes(self._stderr_tail).decode(
                "utf-8", errors="replace"
            ).strip()
        code_label = returncode if returncode is not None else "desconhecido"
        message = f"Captura de áudio encerrada inesperadamente (código {code_label})"
        if detail:
            message += f": {detail}"
        with self._lock:
            self.error_message = message
            self.state = PlaybackState.FAILED

    def _cleanup_resources(self, process, *threads) -> list[str]:
        errors = []
        if process is not None:
            try:
                process.terminate()
            except Exception as exc:
                errors.append(f"terminate: {exc}")
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                    process.wait(timeout=1.0)
                except Exception as exc:
                    errors.append(f"kill: {exc}")
            except Exception as exc:
                errors.append(f"wait: {exc}")
        for stream_name in ("stdout", "stderr"):
            stream = getattr(process, stream_name, None) if process is not None else None
            close = getattr(stream, "close", None)
            if close is not None:
                try:
                    close()
                except Exception as exc:
                    errors.append(f"close {stream_name}: {exc}")
        for thread in threads:
            if thread is None or thread is threading.current_thread():
                continue
            try:
                thread.join(timeout=1.0)
                is_alive = getattr(thread, "is_alive", lambda: False)
                if is_alive():
                    errors.append("join: thread de captura não encerrou")
            except Exception as exc:
                errors.append(f"join: {exc}")
        return errors

    def get_position_seconds(self) -> float:
        with self._lock:
            captured_samples = self._captured_samples
        return captured_samples / self.samplerate

    def get_next_frame(self) -> Optional[AudioFrame]:
        with self._lock:
            if self._available_samples < self.frame_size:
                if self.state is PlaybackState.FAILED:
                    raise AudioPlaybackError(
                        self.error_message or "Falha desconhecida na captura de áudio"
                    )
                return None
            start = self._analysis_cursor
            samples = np.empty(self.frame_size, dtype=np.float32)
            write_cursor = 0
            while write_cursor < self.frame_size:
                chunk = self._sample_chunks[0]
                copied = min(len(chunk), self.frame_size - write_cursor)
                samples[write_cursor : write_cursor + copied] = chunk[:copied]
                write_cursor += copied
                if copied == len(chunk):
                    self._sample_chunks.popleft()
                else:
                    self._sample_chunks[0] = chunk[copied:]
            self._available_samples -= self.frame_size
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
        with self._lifecycle_lock:
            self._stop()

    def _stop(self) -> None:
        with self._lock:
            process = self._process
            thread = self._thread
            stderr_thread = self._stderr_thread
            self._process = None
            self._thread = None
            self._stderr_thread = None
            self._stop_event.set()
            if self.state is not PlaybackState.FAILED:
                self.state = PlaybackState.STOPPED

        cleanup_errors = self._cleanup_resources(process, thread, stderr_thread)
        if cleanup_errors:
            with self._lock:
                self.error_message = "Falha ao liberar captura de áudio (" + "; ".join(
                    cleanup_errors
                ) + ")"
