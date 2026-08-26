"""
audio/input.py (v4 - Linux Compatible com sounddevice)

Substitui pygame.mixer por sounddevice para reprodução confiável no Linux.
Mantém a mesma API pública (play, get_position_seconds, get_next_frame).
"""

from dataclasses import dataclass
import time
import threading
from typing import Optional
import numpy as np
import soundfile as sf
import sounddevice as sd


@dataclass
class AudioFrame:
    """Um pequeno pedaço temporal de áudio, pronto para análise."""
    samples: np.ndarray
    timestamp: float
    samplerate: int
    frame_index: int


class AudioInput:
    def __init__(self, file_path: str, frame_duration: float = 1.0 / 30.0):
        self.file_path = file_path
        self.frame_duration = frame_duration

        # Carrega áudio completo na memória (float32, mono)
        data, samplerate = sf.read(file_path, dtype="float32", always_2d=True)
        data = data.mean(axis=1)  # stereo -> mono

        self.samples = data
        self.samplerate = samplerate
        self.total_samples = len(data)
        self.frame_size = max(1, int(self.samplerate * self.frame_duration))
        self.total_duration = len(data) / samplerate

        # Estado de reprodução
        self._playing = False
        self._finished = False
        self._last_frame_index = -1
        self._play_start_time: Optional[float] = None
        self._stream: Optional[sd.OutputStream] = None
        self._stream_start_time: Optional[float] = None
        self._lock = threading.Lock()

        # Verifica dispositivos de saída disponíveis
        self._device_available = self._check_audio_device()

    def _check_audio_device(self) -> bool:
        """Verifica se há dispositivo de saída de áudio disponível."""
        try:
            devices = sd.query_devices()
            output_devices = [d for d in devices if d['max_output_channels'] > 0]
            if not output_devices:
                print("[AVISO] Nenhum dispositivo de saída de áudio encontrado")
                return False
            # Tenta abrir stream de teste
            with sd.OutputStream(samplerate=self.samplerate, channels=1, dtype='float32'):
                pass
            print("[INFO] Dispositivo de áudio detectado e testado com sucesso")
            return True
        except Exception as e:
            print(f"[AVISO] Dispositivo de áudio não disponível ({e}), modo offline")
            return False

    def play(self) -> None:
        """Inicia a reprodução de áudio (ou modo offline se sem dispositivo)."""
        with self._lock:
            if self._playing:
                return

            self._playing = True
            self._finished = False
            self._last_frame_index = -1
            self._play_start_time = None
            self._stream_start_time = None

            if self._device_available:
                try:
                    # Cria stream de saída não-bloqueante
                    self._stream = sd.OutputStream(
                        samplerate=self.samplerate,
                        channels=1,
                        dtype='float32',
                        callback=self._audio_callback,
                        finished_callback=self._playback_finished
                    )
                    self._stream.start()
                    self._stream_start_time = time.time()
                    print("[INFO] Reprodução de áudio iniciada (sounddevice)")
                except Exception as e:
                    print(f"[ERRO] Falha ao iniciar stream ({e}) - modo offline")
                    self._device_available = False
                    self._stream = None

            if not self._device_available:
                # Modo offline: apenas marca tempo inicial
                self._play_start_time = time.time()
                print("[INFO] Modo offline iniciado (sem reprodução de áudio)")

    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info, status) -> None:
        """Callback do sounddevice para preencher buffer de saída."""
        if status:
            print(f"[AVISO] Stream status: {status}")

        current_pos = self._get_stream_position_samples()
        end_pos = current_pos + frames

        if current_pos >= self.total_samples:
            outdata.fill(0)
            raise sd.CallbackStop()

        chunk = self.samples[current_pos:end_pos]
        if len(chunk) < frames:
            outdata[:len(chunk), 0] = chunk
            outdata[len(chunk):, 0] = 0
            raise sd.CallbackStop()
        else:
            outdata[:, 0] = chunk

    def _playback_finished(self) -> None:
        """Callback chamado quando stream termina naturalmente."""
        with self._lock:
            self._finished = True
            self._playing = False
            if self._stream:
                self._stream.close()
                self._stream = None
            print("[INFO] Reprodução finalizada")

    def _get_stream_position_samples(self) -> int:
        """Obtém posição atual do stream em samples."""
        if self._stream and self._stream_start_time is not None:
            elapsed = time.time() - self._stream_start_time
            return int(elapsed * self.samplerate)
        return 0

    def is_finished(self) -> bool:
        with self._lock:
            return self._finished

    def get_position_seconds(self) -> float:
        """Posição atual de reprodução, em segundos."""
        with self._lock:
            if self._device_available and self._stream and self._stream_start_time is not None:
                try:
                    # Usa tempo do stream para precisão
                    elapsed = time.time() - self._stream_start_time
                    pos = max(0.0, min(elapsed, self.total_duration))
                    return pos
                except Exception:
                    pass

            # Fallback: modo offline ou erro no stream
            if self._play_start_time is None:
                return 0.0
            elapsed = time.time() - self._play_start_time
            return max(0.0, min(elapsed, self.total_duration))

    def get_next_frame(self) -> Optional[AudioFrame]:
        """
        Retorna o próximo AudioFrame correspondente à posição atual,
        ou None se ainda não houver frame novo disponível.
        """
        with self._lock:
            if not self._playing:
                return None

            # Inicializa relógio offline na primeira chamada
            if self._play_start_time is None:
                self._play_start_time = time.time()

            # Verifica se stream ainda ativo (modo online)
            if self._device_available:
                try:
                    if self._stream is None or not self._stream.active:
                        if not self._finished:
                            self._finished = True
                            self._playing = False
                        return None
                except Exception:
                    pass

            position = self.get_position_seconds()

            # Verifica fim de áudio (modo offline ou fim natural)
            if position >= self.total_duration:
                if not self._finished:
                    self._finished = True
                    self._playing = False
                    if self._stream:
                        try:
                            self._stream.stop()
                            self._stream.close()
                        except Exception:
                            pass
                        self._stream = None
                return None

            frame_index = int(position * self.samplerate / self.frame_size)

            if frame_index == self._last_frame_index:
                return None  # mesmo frame temporal

            start = frame_index * self.frame_size
            end = start + self.frame_size

            if start >= self.total_samples:
                self._finished = True
                self._playing = False
                return None

            chunk = self.samples[start:end]
            if len(chunk) < self.frame_size:
                chunk = np.pad(chunk, (0, self.frame_size - len(chunk)))

            self._last_frame_index = frame_index

            return AudioFrame(
                samples=chunk,
                timestamp=position,
                samplerate=self.samplerate,
                frame_index=frame_index,
            )

    def stop(self) -> None:
        """Para a reprodução imediatamente."""
        with self._lock:
            self._playing = False
            self._finished = True
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            print("[INFO] Reprodução parada")

    def __del__(self):
        self.stop()
