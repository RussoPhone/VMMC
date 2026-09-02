from collections import deque
from dataclasses import dataclass, field
from statistics import fmean, pstdev

from memory.adaptive_landscape import AdaptiveLandscape, RelativeFeatures


def _clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


@dataclass(frozen=True)
class MusicalContext:
    energy: float
    short_energy: float
    medium_energy: float
    energy_trend: float
    activity: float
    activity_trend: float
    novelty: float
    stability: float
    tension: float
    persistence: float
    spectral_centroid: float
    zero_crossing_rate: float
    spectral_density: float
    onset: bool
    relative: RelativeFeatures = field(
        default_factory=lambda: RelativeFeatures(0.0, 0.0, 0.0, 0.0, 0.0)
    )
    signature: "SoundSignature" = field(
        default_factory=lambda: SoundSignature(0.0, 0.0, 0.0, 0.0, 0.0)
    )
    signature_continuity: float = 0.0
    prominence: float = 0.0

    @property
    def energy_average(self):
        return self.short_energy


@dataclass(frozen=True)
class _MemorySample:
    timestamp: float
    energy: float
    activity: float
    centroid: float
    zcr: float
    density: float
    spectral_stability: float


@dataclass(frozen=True)
class SoundSignature:
    brightness: float
    noisiness: float
    harmonicity: float
    attack: float
    density: float


class MusicalMemory:
    def __init__(
        self,
        short_window_seconds: float = 2.0,
        medium_window_seconds: float = 12.0,
        activity_smoothing: float = 0.15,
        window_seconds: float | None = None,
    ):
        if window_seconds is not None:
            short_window_seconds = window_seconds
        self.short_window_seconds = short_window_seconds
        self.medium_window_seconds = max(medium_window_seconds, short_window_seconds)
        self.activity_smoothing = activity_smoothing
        self._history = deque()
        self._smoothed_activity = 0.0
        self._tension = 0.0
        self._persistence = 0.0
        self._landscape = AdaptiveLandscape()
        self._signature_history = deque(maxlen=360)

    def update(self, features) -> MusicalContext:
        relative = self._landscape.update(features)
        signature = SoundSignature(
            brightness=_clamp(getattr(features, "spectral_centroid", 0.0)),
            noisiness=_clamp(getattr(features, "spectral_flatness", 0.0)),
            harmonicity=_clamp(getattr(features, "harmonicity", 0.0)),
            attack=_clamp(getattr(features, "attack_strength", 0.0)),
            density=_clamp(getattr(features, "spectral_density", 0.0)),
        )
        signature_continuity = self._signature_continuity(signature)

        self._smoothed_activity += (
            features.spectral_flux - self._smoothed_activity
        ) * self.activity_smoothing

        sample = _MemorySample(
            timestamp=features.timestamp,
            energy=_clamp(features.amplitude),
            activity=_clamp(self._smoothed_activity),
            centroid=_clamp(getattr(features, "spectral_centroid", 0.0)),
            zcr=_clamp(getattr(features, "zero_crossing_rate", 0.0)),
            density=_clamp(getattr(features, "spectral_density", 0.0)),
            spectral_stability=_clamp(
                getattr(features, "spectral_stability", 0.0)
            ),
        )
        self._history.append(sample)
        self._prune(features.timestamp)

        short = self._samples_since(features.timestamp - self.short_window_seconds)
        medium = list(self._history)
        short_energy = fmean(item.energy for item in short)
        medium_energy = fmean(item.energy for item in medium)
        short_activity = fmean(item.activity for item in short)
        medium_activity = fmean(item.activity for item in medium)
        energy_trend = _clamp(short_energy - medium_energy, -1.0, 1.0)
        activity_trend = _clamp(short_activity - medium_activity, -1.0, 1.0)

        centroid_average = fmean(item.centroid for item in short)
        activity_average = fmean(item.activity for item in short)
        novelty = _clamp(
            abs(sample.energy - short_energy) * 0.45
            + abs(sample.centroid - centroid_average) * 0.25
            + abs(sample.activity - activity_average) * 0.20
            + (1.0 - sample.spectral_stability) * 0.10
        )

        energy_variation = min(1.0, pstdev(item.energy for item in short) * 4.0)
        spectral_stability = fmean(item.spectral_stability for item in short)
        stability = _clamp(
            spectral_stability * 0.65
            + (1.0 - energy_variation) * 0.35
            - novelty * 0.35
        )

        tension_target = _clamp(
            max(0.0, energy_trend) * 1.5
            + max(0.0, activity_trend) * 1.2
            + sample.activity * 0.45
            + novelty * 0.35
        )
        tension_rate = 0.12 if tension_target > self._tension else 0.025
        self._tension += (tension_target - self._tension) * tension_rate

        persistence_target = max(sample.energy, short_energy, self._tension)
        persistence_rate = 0.15 if persistence_target > self._persistence else 0.015
        self._persistence += (
            persistence_target - self._persistence
        ) * persistence_rate

        prominence = _clamp(
            max(0.0, relative.energy) * 0.25
            + max(0.0, relative.brightness) * 0.10
            + max(0.0, relative.texture) * 0.15
            + max(0.0, relative.activity) * 0.20
            + novelty * 0.15
            + signature.attack * 0.10
            + signature_continuity * 0.05
        )
        self._signature_history.append(signature)

        return MusicalContext(
            energy=sample.energy,
            short_energy=_clamp(short_energy),
            medium_energy=_clamp(medium_energy),
            energy_trend=energy_trend,
            activity=sample.activity,
            activity_trend=activity_trend,
            novelty=novelty,
            stability=stability,
            tension=_clamp(self._tension),
            persistence=_clamp(self._persistence),
            spectral_centroid=_clamp(fmean(item.centroid for item in short)),
            zero_crossing_rate=_clamp(fmean(item.zcr for item in short)),
            spectral_density=_clamp(fmean(item.density for item in short)),
            onset=bool(features.beat),
            relative=relative,
            signature=signature,
            signature_continuity=signature_continuity,
            prominence=prominence,
        )

    def _signature_continuity(self, signature: SoundSignature) -> float:
        if not self._signature_history:
            return 0.0
        recent = list(self._signature_history)[-90:]
        return max(1.0 - self._signature_distance(signature, item) for item in recent)

    @staticmethod
    def _signature_distance(left: SoundSignature, right: SoundSignature) -> float:
        return fmean(
            abs(left_value - right_value)
            for left_value, right_value in zip(
                vars(left).values(), vars(right).values()
            )
        )

    def _prune(self, current_timestamp: float) -> None:
        while (
            self._history
            and current_timestamp - self._history[0].timestamp
            > self.medium_window_seconds
        ):
            self._history.popleft()

    def _samples_since(self, earliest_timestamp):
        return [
            sample for sample in self._history if sample.timestamp >= earliest_timestamp
        ]
