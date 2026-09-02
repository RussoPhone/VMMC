import math
import unittest

from audio.analyzer import AudioFeatures
from memory.adaptive_landscape import AdaptiveLandscape


def features(
    timestamp,
    amplitude,
    centroid=0.3,
    flux=0.0,
    flatness=0.2,
    density=0.3,
    attack=0.0,
):
    return AudioFeatures(
        timestamp=timestamp,
        amplitude=amplitude,
        bass=0.0,
        mid=0.0,
        treble=0.0,
        spectral_flux=flux,
        beat=False,
        spectral_centroid=centroid,
        spectral_density=density,
        spectral_flatness=flatness,
        attack_strength=attack,
    )


class AdaptiveLandscapeTests(unittest.TestCase):
    def test_same_detail_is_stronger_after_calm_than_intense_history(self):
        calm = AdaptiveLandscape()
        intense = AdaptiveLandscape()
        for index in range(180):
            calm.update(features(index / 30.0, amplitude=0.05, centroid=0.2))
            intense.update(features(index / 30.0, amplitude=0.75, centroid=0.7))

        detail = features(6.0, amplitude=0.25, centroid=0.45, flux=0.15)
        calm_relative = calm.update(detail)
        intense_relative = intense.update(detail)

        self.assertGreater(
            calm_relative.energy, intense_relative.energy + 0.35
        )
        self.assertGreater(
            calm_relative.brightness, intense_relative.brightness + 0.35
        )

    def test_steady_intensity_becomes_the_landscape_baseline(self):
        landscape = AdaptiveLandscape()
        first = landscape.update(features(0.0, amplitude=0.6, flux=0.5))
        current = first
        for index in range(1, 240):
            current = landscape.update(
                features(index / 30.0, amplitude=0.6, flux=0.5)
            )

        self.assertGreater(current.confidence, 0.8)
        self.assertLess(abs(current.energy), 0.1)
        self.assertLess(abs(current.activity), 0.1)
        self.assertAlmostEqual(landscape.energy_baseline, 0.6, delta=0.02)

    def test_reset_starts_a_new_uncertain_landscape(self):
        landscape = AdaptiveLandscape()
        sample = features(0.0, amplitude=0.4, centroid=0.6, flux=0.2)
        for index in range(200):
            landscape.update(
                features(index / 30.0, amplitude=0.4, centroid=0.6, flux=0.2)
            )

        landscape.reset()
        relative = landscape.update(sample)

        self.assertLess(relative.confidence, 0.01)
        self.assertAlmostEqual(relative.energy, 0.0)
        self.assertAlmostEqual(relative.brightness, 0.0)

    def test_outputs_are_finite_and_bounded(self):
        landscape = AdaptiveLandscape()
        samples = [
            features(0.0, amplitude=0.0, centroid=0.0),
            features(1.0, amplitude=1.0, centroid=1.0, flux=1.0, flatness=1.0),
        ]

        for sample in samples:
            relative = landscape.update(sample)
            for value in (
                relative.energy,
                relative.brightness,
                relative.texture,
                relative.activity,
            ):
                self.assertTrue(math.isfinite(value))
                self.assertGreaterEqual(value, -1.0)
                self.assertLessEqual(value, 1.0)
            self.assertGreaterEqual(relative.confidence, 0.0)
            self.assertLessEqual(relative.confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
