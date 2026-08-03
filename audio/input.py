"""
audio/input.py (v3 FINAL)

Versão que REALMENTE tolera mixer indisponível.
Nenhuma tentativa de acessar pygame.mixer sem try/except.
"""

from dataclasses import dataclass
import time
import numpy as np
import soundfile as sf
import pygame


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

        data, samplerate = sf.read(file_path, dtype="float32", always_2d=True)
        data = data.mean(axis=1)

        self.samples = data
        self.samplerate = samplerate
        self.total_samples = len(data)
        self.frame_size = max(1, int(self.samplerate * self.frame_duration))
        self.total_duration = len(data) / samplerate

        self._last_frame_index = -1
        self._playing = False
        self._finished = False
        self._play_start_time = None
        
        # Detecta se mixer está disponível
        self._mixer_available = False
        try:
            # Testa se mixer consegue ser importado e inicializado
            pygame.mixer.init()
            self._mixer_available = True
        except (AttributeError, NotImplementedError, Exception):
            self._mixer_available = False
            print("[AVISO] pygame.mixer nao disponivel, exec modo offline")

    def play(self) -> None:
        """Inicia a reprodução (ou modo offline se mixer indisponível)."""
        if self._mixer_available:
            try:
                pygame.mixer.music.load(self.file_path)
                pygame.mixer.music.play()
            except Exception as e:
                print(f"[AVISO] Falha ao tocar audio ({e}) - modo offline")
                self._mixer_available = False

        self._playing = True
        self._finished = False
        self._last_frame_index = -1
        self._play_start_time = None

    def is_finished(self) -> bool:
        return self._finished

    def get_position_seconds(self) -> float:
        """Posição atual de reprodução, em segundos."""
        if self._mixer_available:
            try:
                if pygame.mixer.music.get_busy():
                    pos_ms = pygame.mixer.music.get_pos()
                    if pos_ms >= 0:
                        return pos_ms / 1000.0
            except Exception:
                pass

        # Modo offline: usa tempo real decorrido desde play()
        if self._play_start_time is None:
            return 0.0
        
        return time.time() - self._play_start_time

    def get_next_frame(self):
        """
        Retorna o próximo AudioFrame correspondente à posição atual de
        reprodução, ou None se ainda não houver um frame novo disponível.
        """
        if not self._playing:
            return None

        # Inicializa relógio offline na primeira chamada após play()
        if self._play_start_time is None:
            self._play_start_time = time.time()

        # Verifica se o áudio ainda está tocando (modo online)
        if self._mixer_available:
            try:
                if not pygame.mixer.music.get_busy():
                    self._finished = True
                    self._playing = False
                    return None
            except Exception:
                pass

        position = self.get_position_seconds()

        # Modo offline: verifica se ultrapassou a duração total
        if position >= self.total_duration:
            self._finished = True
            self._playing = False
            return None

        frame_index = int(position * self.samplerate / self.frame_size)

        if frame_index == self._last_frame_index:
            return None  # ainda no mesmo frame temporal, nada novo

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
