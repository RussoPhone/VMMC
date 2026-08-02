from collections import deque
from dataclasses import dataclass 

@dataclass  
class MusicalContext:
    energy: float
    energy_average: float
    energy_trend: float 
    activity: float 
    tension: float 

class MusicalMemory:
    def __init__(self, window_seconds: float = 4.0, activity_smoothing: float = 0.15):
        self.window_seconds = window_seconds
        self.activity_smoothing = activity_smoothing

        self._history = deque()
        self._smoothed_activity = 0.0

    def update(self, features) -> MusicalContext:
        self._history.append((features.timestamp, features.amplitude))
        self._prune(features.timestamp)
        
        energy = features.amplitude
        energy_average = self._average_energy()
        energy_trend =energy - energy_average

        self._smoothed_activity += (
            features.spectral_flux - self._smoothed_activity
        ) * self.activity_smoothing
        activity = self._smoothed_activity

        tension = self._compute_tension(energy_trend, activity)

        return MusicalContext(
            energy=energy,
            energy_average=energy_average,
            energy_trend=energy_trend,
            activity=activity,
            tension=tension,
        )
    
    def _prune(self, current_timestamp: float) -> None:
        while self._history and (current_timestamp - self._history[0][0]) > self.window_seconds:
            self._history.popleft()
    def _average_energy(self) -> float:
        if not self._history:
            return 0.0
        return sum(a for _, a in self._history) / len(self._history)

    def _compute_tension(self, energy_trend: float, activity: float) -> float:

        raw = abs(energy_trend) * 1.5 + activity * 0.8
        return max(0.0, min(1.0, raw))
        
