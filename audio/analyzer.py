from dataclasses import dataclass
from collections import deque
import math
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
    spectral_flatness: float = 0.0
    harmonicity: float = 0.0
    attack_strength: float = 0.0
    spectral_spread: float = 0.0
    cqt_notes: tuple = ()
    cqt_frequencies: tuple = ()
    local_activity: tuple = (0.0, 0.0, 0.0)
    local_novelty: tuple = (0.0, 0.0, 0.0)
    vocal_evidence: float = 0.0
    vocal_intensity: float = 0.0

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
        self._prev_rms = None
        self._cqt_samplerate = None
        self._cqt_buffer = np.zeros(0, dtype=np.float64)
        self._cqt_frequencies = np.zeros(0, dtype=np.float64)
        self._cqt_kernels = ()
        self._local_history = tuple(deque(maxlen=45) for _ in range(3))

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
        flatness = self._compute_spectral_flatness(spectrum)
        harmonicity = max(0.0, min(1.0, 1.0 - flatness))
        attack_strength = self._compute_attack_strength(samples)
        spread = self._compute_spectral_spread(spectrum, sr, len(samples))
        cqt_notes = self._compute_cqt(samples, sr)
        local_activity, local_novelty = self._compute_local_novelty(cqt_notes)
        vocal_evidence, vocal_intensity = self._compute_vocal_evidence(
            cqt_notes,
            amplitude,
            flatness,
            centroid,
            local_activity,
        )

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
            spectral_flatness=flatness,
            harmonicity=harmonicity,
            attack_strength=attack_strength,
            spectral_spread=spread,
            cqt_notes=tuple(float(value) for value in cqt_notes),
            cqt_frequencies=tuple(float(value) for value in self._cqt_frequencies),
            local_activity=local_activity,
            local_novelty=local_novelty,
            vocal_evidence=vocal_evidence,
            vocal_intensity=vocal_intensity,
        )

    def _prepare_cqt(self, samplerate):
        if samplerate == self._cqt_samplerate:
            return
        upper = min(8_000.0, samplerate * .475)
        count = max(1, int(math.floor(12 * math.log2(upper / 55.0))) + 1)
        self._cqt_frequencies = 55.0 * 2 ** (np.arange(count) / 12.0)
        quality = 1.0 / (2 ** (1 / 12) - 1)
        kernels = []
        for frequency in self._cqt_frequencies:
            length = max(32, int(math.ceil(quality * samplerate / frequency)))
            window = np.hanning(length)
            phase = np.exp(-2j * np.pi * frequency * np.arange(length) / samplerate)
            kernels.append(window * phase / max(float(window.sum()), 1e-12))
        self._cqt_kernels = tuple(kernels)
        self._cqt_samplerate = samplerate
        self._cqt_buffer = np.zeros(0, dtype=np.float64)
        self._local_history = tuple(deque(maxlen=45) for _ in range(3))

    def _compute_cqt(self, samples, samplerate):
        self._prepare_cqt(samplerate)
        maximum = max(len(kernel) for kernel in self._cqt_kernels)
        incoming = np.asarray(samples, dtype=np.float64)
        self._cqt_buffer = np.concatenate((self._cqt_buffer, incoming))[-maximum:]
        values = []
        for kernel in self._cqt_kernels:
            available = min(len(kernel), len(self._cqt_buffer))
            if available < 16:
                values.append(0.0)
                continue
            partial = kernel[-available:]
            normalization = max(float(np.sum(np.abs(partial))), 1e-12)
            values.append(
                abs(np.dot(self._cqt_buffer[-available:], partial)) / normalization
            )
        return np.asarray(values, dtype=np.float64)

    def _compute_local_novelty(self, cqt_notes):
        ranges = (self.bass_range, self.mid_range, self.treble_range)
        floors = (.012, .008, .0035)
        activity = []
        novelty = []
        for index, ((low, high), floor) in enumerate(zip(ranges, floors)):
            mask = (self._cqt_frequencies >= low) & (self._cqt_frequencies < high)
            region = cqt_notes[mask]
            strongest = np.sort(region)[-3:] if len(region) else np.zeros(1)
            current = 1.0 - math.exp(-float(np.mean(strongest)) * 18.0)
            history = self._local_history[index]
            baseline = float(np.median(history)) if history else 0.0
            increase = max(0.0, current - baseline)
            novelty.append(1.0 - math.exp(-increase / (floor + baseline * .5)))
            activity.append(current)
            history.append(current)
        return tuple(activity), tuple(novelty)

    def _compute_vocal_evidence(
        self,
        cqt_notes,
        amplitude,
        flatness,
        centroid,
        local_activity,
    ):
        candidates = np.flatnonzero(
            (self._cqt_frequencies >= 80) & (self._cqt_frequencies <= 350)
        )
        weights = (1.0, .8, .62, .48, .36, .28)
        harmonic_score = 0.0
        peak = max(float(np.max(cqt_notes)), 1e-12)
        for candidate in candidates:
            fundamental = self._cqt_frequencies[candidate]
            harmonic_sum = 0.0
            weight_sum = 0.0
            for harmonic, weight in enumerate(weights, start=1):
                target = fundamental * harmonic
                if target > 4_000:
                    break
                note = int(np.argmin(np.abs(self._cqt_frequencies - target)))
                harmonic_sum += float(cqt_notes[note]) * weight
                weight_sum += weight
            harmonic_score = max(
                harmonic_score,
                harmonic_sum / max(peak * weight_sum, 1e-12),
            )
        harmonic_score = max(0.0, min(1.0, harmonic_score))
        voice_center = math.exp(-((centroid - .075) / .095) ** 2)
        tonal = 1.0 - flatness
        gate = 1.0 - math.exp(-amplitude * 12.0)
        evidence = gate * (
            tonal * .45
            + harmonic_score * .28
            + local_activity[1] * .17
            + voice_center * .10
        )
        evidence = max(0.0, min(1.0, evidence))
        intensity = evidence * min(
            1.0,
            local_activity[1] * .72 + amplitude * 1.4,
        )
        return evidence, max(0.0, min(1.0, intensity))
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

    def _compute_spectral_flatness(self, spectrum: np.ndarray) -> float:
        if len(spectrum) == 0 or float(np.max(spectrum)) <= 1e-12:
            return 0.0
        magnitudes = spectrum + 1e-12
        geometric_mean = float(np.exp(np.mean(np.log(magnitudes))))
        arithmetic_mean = float(np.mean(magnitudes))
        return max(0.0, min(1.0, geometric_mean / arithmetic_mean))

    def _compute_attack_strength(self, samples: np.ndarray) -> float:
        rms = float(np.sqrt(np.mean(samples ** 2) + 1e-12))
        if self._prev_rms is None:
            attack = 0.0
        else:
            attack = max(0.0, min(1.0, (rms - self._prev_rms) * 8.0))
        self._prev_rms = rms
        return attack

    def _compute_spectral_spread(self, spectrum, sr, n_samples) -> float:
        total = float(np.sum(spectrum))
        if total <= 1e-12:
            return 0.0
        freqs = np.fft.rfftfreq(n_samples, d=1.0 / sr)
        centroid = float(np.sum(freqs * spectrum) / total)
        variance = float(np.sum(((freqs - centroid) ** 2) * spectrum) / total)
        spread_hz = float(np.sqrt(max(0.0, variance)))
        return max(0.0, min(1.0, spread_hz / (sr * 0.5)))

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
