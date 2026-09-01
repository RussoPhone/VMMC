"""Audio decoding, playback, and analysis-frame synchronization."""

from dataclasses import dataclass
from enum import Enum
import threading
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import soundfile as sf


class PlaybackState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    FINISHED = "finished"
    FAILED = "failed"


class AudioPlaybackError(RuntimeError):
    """Raised when an audio output stream cannot be started."""


@dataclass
class AudioFrame:
    """A fixed-duration mono frame ready for musical analysis."""

    samples: np.ndarray
    timestamp: float
    samplerate: int
    frame_index: int


class AudioInput:
    def __init__(
        self,
        file_path: str,
        frame_duration: float = 1.0 / 30.0,
        stream_factory: Optional[Callable[..., object]] = None,
    ):
        playback_samples, samplerate = sf.read(
            file_path,
            dtype="float32",
            always_2d=True,
        )

        self.file_path = file_path
        self.frame_duration = frame_duration
        self._playback_samples = np.ascontiguousarray(playback_samples)
        self._analysis_samples = self._playback_samples.mean(axis=1)
        self.samples = self._analysis_samples
        self.samplerate = samplerate
        self.channels = self._playback_samples.shape[1]
        self.total_samples = len(self._playback_samples)
        self.frame_size = max(1, int(self.samplerate * self.frame_duration))
        self.total_duration = self.total_samples / self.samplerate

        self._stream_factory = stream_factory or sd.OutputStream
        self._stream = None
        self._playback_cursor = 0
        self._analysis_cursor = 0
        self._lock = threading.Lock()
        self._output_finished = threading.Event()

        self.state = PlaybackState.STOPPED
        self.error_message: Optional[str] = None

    def play(self) -> None:
        """Start output through the configured SoundDevice-compatible stream."""
        with self._lock:
            if self.state is PlaybackState.PLAYING:
                return

        self.stop()

        with self._lock:
            self._playback_cursor = 0
            self._analysis_cursor = 0
            self._output_finished.clear()
            self.error_message = None
            self.state = PlaybackState.PLAYING

        try:
            stream = self._stream_factory(
                samplerate=self.samplerate,
                channels=self.channels,
                dtype="float32",
                callback=self._audio_callback,
                finished_callback=self._playback_finished,
            )
            with self._lock:
                self._stream = stream
            stream.start()
        except Exception as exc:
            with self._lock:
                failed_stream = self._stream
                self._stream = None
                self.state = PlaybackState.FAILED
                self.error_message = str(exc)
            if failed_stream is not None:
                try:
                    failed_stream.close()
                except Exception:
                    pass
            raise AudioPlaybackError(f"Falha ao iniciar a saída de áudio: {exc}") from exc

    def _audio_callback(self, outdata, frames, time_info, status) -> None:
        """Fill one output buffer with the next contiguous source samples."""
        del time_info, status
        outdata.fill(0)

        with self._lock:
            if self.state is not PlaybackState.PLAYING:
                raise sd.CallbackStop()
            start = self._playback_cursor

        end = min(start + frames, self.total_samples)
        copied = end - start
        if copied > 0:
            outdata[:copied] = self._playback_samples[start:end]

        with self._lock:
            self._playback_cursor = end

        if end >= self.total_samples:
            raise sd.CallbackStop()

    def _playback_finished(self) -> None:
        """Record natural completion without closing from the callback thread."""
        self._output_finished.set()
        with self._lock:
            if self.state is PlaybackState.PLAYING:
                self.state = PlaybackState.FINISHED

    def get_position_seconds(self) -> float:
        """Return the sample-driven output position in seconds."""
        with self._lock:
            cursor = self._playback_cursor
        return cursor / self.samplerate

    def get_next_frame(self) -> Optional[AudioFrame]:
        """Return the next elapsed analysis frame, preserving temporal order."""
        with self._lock:
            if self.state not in (PlaybackState.PLAYING, PlaybackState.FINISHED):
                return None

            start = self._analysis_cursor
            if start >= self.total_samples:
                return None

            end = min(start + self.frame_size, self.total_samples)
            frame_is_ready = end <= self._playback_cursor
            tail_is_ready = self._output_finished.is_set()
            if not frame_is_ready and not tail_is_ready:
                return None

            self._analysis_cursor = end
            frame_index = start // self.frame_size

        chunk = self._analysis_samples[start:end]
        if len(chunk) < self.frame_size:
            chunk = np.pad(chunk, (0, self.frame_size - len(chunk)))

        return AudioFrame(
            samples=chunk,
            timestamp=start / self.samplerate,
            samplerate=self.samplerate,
            frame_index=frame_index,
        )

    def is_finished(self) -> bool:
        """Return true after natural output and all analysis frames complete."""
        with self._lock:
            return (
                self.state is PlaybackState.FINISHED
                and self._analysis_cursor >= self.total_samples
            )

    def stop(self) -> None:
        """Stop and close the output stream. Safe to call repeatedly."""
        with self._lock:
            stream = self._stream
            self._stream = None
            if self.state is not PlaybackState.FAILED:
                self.state = PlaybackState.STOPPED

        if stream is None:
            return

        try:
            if getattr(stream, "active", False):
                stream.stop()
        finally:
            stream.close()

    def __del__(self):
        if hasattr(self, "_lock"):
            try:
                self.stop()
            except Exception:
                pass
