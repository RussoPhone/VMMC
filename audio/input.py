from dataclasses import dataclass

import numpy as np
import pygame
import soundfile as sf   

@dataclass 
class AudioFrame:
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

        self._last_frame_index = -1
        self._playing = False
        self._finished = False 

        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=self.samplerate)

    def play(self) -> None:
        pygame.mixer.music.load(self.file_path)
        pygame.mixer.music.play()
        self._playing = True
        self._finished = False
        self._last_frame_index = -1

    def is_finished(self) -> bool:
        return self._finished
    
    def get_position_seconds(self) -> float:
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms < 0:
            return 0.0
        return pos_ms / 1000.0
    
    def get_next_frame(self):
        if not self._playing:
            return None
        if not pygame.mixer.music.get_busy():
            self._finished = True
            self._playing = False
            return None
        position = self.get_position_seconds()
        frame_index = int(position * self.samplerate / self.frame_size)

        if frame_index == self._last_frame_index:
            return None
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



