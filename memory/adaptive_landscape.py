"""Music-relative normalization for adaptive contextual listening."""

from dataclasses import dataclass
import math


def _clamp(value, low, high):
    return max(low, min(high, value))


@dataclass(frozen=True)
class RelativeFeatures:
    energy: float
    brightness: float
    texture: float
    activity: float
    confidence: float


@dataclass
class _RunningStatistic:
    short_mean: float = 0.0
    short_variance: float = 0.0
    long_mean: float = 0.0
    long_variance: float = 0.0
    initialized: bool = False

    def initialize(self, value: float) -> None:
        self.short_mean = value
        self.long_mean = value
        self.short_variance = 0.0
        self.long_variance = 0.0
        self.initialized = True

    def update(self, value: float, short_rate: float, long_rate: float) -> None:
        self.short_mean, self.short_variance = self._step(
            self.short_mean, self.short_variance, value, short_rate
        )
        self.long_mean, self.long_variance = self._step(
            self.long_mean, self.long_variance, value, long_rate
        )

    @staticmethod
    def _step(mean, variance, value, rate):
        delta = value - mean
        updated_mean = mean + delta * rate
        updated_variance = (1.0 - rate) * (variance + rate * delta * delta)
        return updated_mean, max(0.0, updated_variance)


class AdaptiveLandscape:
    def __init__(
        self,
        short_rate: float = 0.12,
        long_rate: float = 0.015,
        novelty_hold: float = 0.65,
    ):
        self.short_rate = short_rate
        self.long_rate = long_rate
        self.novelty_hold = novelty_hold
        self.reset()

    @property
    def energy_baseline(self) -> float:
        statistic = self._statistics["energy"]
        if not statistic.initialized:
            return 0.0
        return _clamp(statistic.long_mean, 0.0, 1.0)

    @property
    def confidence(self) -> float:
        return _clamp(self._sample_count / 180.0, 0.0, 1.0)

    def reset(self) -> None:
        self._statistics = {
            name: _RunningStatistic()
            for name in ("energy", "brightness", "texture", "activity")
        }
        self._sample_count = 0

    def update(self, features) -> RelativeFeatures:
        values = {
            "energy": _clamp(features.amplitude, 0.0, 1.0),
            "brightness": _clamp(
                getattr(features, "spectral_centroid", 0.0), 0.0, 1.0
            ),
            "texture": _clamp(
                0.5 * getattr(features, "spectral_flatness", 0.0)
                + 0.5 * getattr(features, "spectral_density", 0.0),
                0.0,
                1.0,
            ),
            "activity": _clamp(
                0.6 * features.spectral_flux
                + 0.4 * getattr(features, "attack_strength", 0.0),
                0.0,
                1.0,
            ),
        }

        if self._sample_count == 0:
            for name, value in values.items():
                self._statistics[name].initialize(value)
            relative_values = {name: 0.0 for name in values}
        else:
            relative_values = {
                name: self._relative_value(self._statistics[name], value)
                for name, value in values.items()
            }
            maximum_deviation = max(abs(value) for value in relative_values.values())
            long_rate = self.long_rate
            if maximum_deviation > self.novelty_hold:
                long_rate *= 0.2
            for name, value in values.items():
                self._statistics[name].update(value, self.short_rate, long_rate)

        self._sample_count += 1
        return RelativeFeatures(
            energy=relative_values["energy"],
            brightness=relative_values["brightness"],
            texture=relative_values["texture"],
            activity=relative_values["activity"],
            confidence=self.confidence,
        )

    def _relative_value(self, statistic: _RunningStatistic, value: float) -> float:
        long_scale = max(math.sqrt(statistic.long_variance), 0.05)
        long_relative = math.tanh(((value - statistic.long_mean) / long_scale) / 2.0)
        if self._sample_count < 30:
            return _clamp(long_relative, -1.0, 1.0)
        short_scale = max(math.sqrt(statistic.short_variance), 0.05)
        short_relative = math.tanh(
            ((value - statistic.short_mean) / short_scale) / 2.0
        )
        return _clamp(long_relative * 0.7 + short_relative * 0.3, -1.0, 1.0)
