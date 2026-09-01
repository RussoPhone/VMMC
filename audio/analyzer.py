from dataclasses import dataclass
import numpy as np 

@dataclass
class AudioFeatures:
    timestamp: float
    amplitude: float 
    bass: float 
    mid: float 
    treble: float 
    spectral_flux: float 
    beat: bool 
    spectral_centroid: float = 0.0
    zero_crossing_rate: float = 0.0
    spectral_density: float = 0.0
    spectral_stability: float = 0.0

class AudioAnalyzer:
    def __init__(
        self,
        bass_range=(20, 250),
        mid_range=(250, 2000),
        treble_range=(2000, 8000),
    ):
        self.bass_range = bass_range
        self.mid_range = mid_range 
        self.treble_range = treble_range 

        self._prev_spectrum = None
        self._flux_history = []
        self._flux_history_max = 43
        self._last_beat_time = -1.0
        self._min_beat_interval = 0.20

    def analyze(self, frame) -> AudioFeatures:
        samples = frame.samples
        sr = frame.samplerate 

        amplitude = self._compute_amplitude(samples)
        spectrum = self._compute_spectrum(samples)
        bass, mid, treble= self._compute_bands(spectrum, sr, len(samples))
        flux = self._compute_spectral_flux(spectrum)
        beat = self._detect_beat(flux, frame.timestamp)
        centroid = self._compute_spectral_centroid(spectrum, sr, len(samples))
        zero_crossing_rate = self._compute_zero_crossing_rate(samples)
        density = self._compute_spectral_density(spectrum)
        stability = self._compute_spectral_stability(spectrum)

        self._prev_spectrum = spectrum

        return AudioFeatures(
            timestamp=frame.timestamp,
            amplitude=amplitude,
            bass=bass,
            mid=mid,
            treble=treble,
            spectral_flux=flux,
            beat=beat,
            spectral_centroid=centroid,
            zero_crossing_rate=zero_crossing_rate,
            spectral_density=density,
            spectral_stability=stability,
        )
    def _compute_amplitude(self, samples: np.ndarray) -> float:
        rms = float(np.sqrt(np.mean(samples ** 2) + 1e-12))
        return min(1.0, rms * 4.0)
    
    def _compute_spectrum(self, samples: np.ndarray) -> np.ndarray:
        window = np.hanning(len(samples))
        return np.abs(np.fft.rfft(samples * window))
    
    def _band_energy(self, spectrum, sr, n_samples, low_hz, high_hz) -> float:
        freqs = np.fft.rfftfreq(n_samples, d=1.0 / sr)
        mask = (freqs >= low_hz) & (freqs < high_hz)
        if not np.any(mask):
            return 0.0
        energy = float(np.mean(spectrum[mask]))
        return min(1.0, energy * 0.05)

    def _compute_bands(self, spectrum, sr, n_samples):
        bass = self._band_energy(spectrum, sr, n_samples, *self.bass_range)
        mid = self._band_energy(spectrum, sr, n_samples, *self.mid_range)
        treble = self._band_energy(spectrum, sr, n_samples, *self.treble_range)
        return bass, mid, treble

    def _compute_spectral_flux(self, spectrum: np.ndarray) -> float:
        if self._prev_spectrum is None or len(self._prev_spectrum) != len(spectrum):
            return 0.0
        diff = spectrum - self._prev_spectrum
        flux = float(np.sum(np.maximum(diff, 0.0)))
        return min(1.0, flux * 0.01)

    def _compute_spectral_centroid(self, spectrum, sr, n_samples) -> float:
        total = float(np.sum(spectrum))
        if total <= 1e-12:
            return 0.0
        freqs = np.fft.rfftfreq(n_samples, d=1.0 / sr)
        centroid_hz = float(np.sum(freqs * spectrum) / total)
        return max(0.0, min(1.0, centroid_hz / (sr * 0.5)))

    def _compute_zero_crossing_rate(self, samples: np.ndarray) -> float:
        if len(samples) < 2:
            return 0.0
        crossings = np.count_nonzero(np.signbit(samples[1:]) != np.signbit(samples[:-1]))
        return float(crossings / (len(samples) - 1))

    def _compute_spectral_density(self, spectrum: np.ndarray) -> float:
        if len(spectrum) == 0:
            return 0.0
        peak = float(np.max(spectrum))
        if peak <= 1e-12:
            return 0.0
        return float(np.count_nonzero(spectrum >= peak * 0.1) / len(spectrum))

    def _compute_spectral_stability(self, spectrum: np.ndarray) -> float:
        if self._prev_spectrum is None or len(self._prev_spectrum) != len(spectrum):
            return 0.0
        distance = float(np.sum(np.abs(spectrum - self._prev_spectrum)))
        magnitude = float(np.sum(spectrum) + np.sum(self._prev_spectrum) + 1e-12)
        return max(0.0, min(1.0, 1.0 - distance / magnitude))

    def _detect_beat(self, flux: float, timestamp: float) -> bool:
        self._flux_history.append(flux)
        if len(self._flux_history) > self._flux_history_max:
            self._flux_history.pop(0)
        avg_flux = sum(self._flux_history) / len(self._flux_history)
        threshold = avg_flux * 1.5 + 0.05
        time_ok = (timestamp - self._last_beat_time) >= self._min_beat_interval

        if flux > threshold and time_ok:
            self._last_beat_time = timestamp
            return True
        return False
