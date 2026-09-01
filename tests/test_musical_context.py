import unittest

from audio.analyzer import AudioFeatures
from memory.musical_memory import MusicalMemory


class MusicalContextTests(unittest.TestCase):
    def test_steady_sequence_is_stable_and_not_novel(self):
        memory = MusicalMemory()
        context = None
        for index in range(180):
            context = memory.update(
                self._features(index / 30.0, energy=0.4, stability=1.0)
            )

        self.assertGreater(context.stability, 0.8)
        self.assertLess(context.novelty, 0.1)
        self.assertAlmostEqual(context.short_energy, context.medium_energy, delta=0.02)

    def test_rising_sequence_builds_trend_and_tension(self):
        memory = MusicalMemory()
        context = None
        for index in range(180):
            energy = 0.1 + 0.7 * index / 179
            context = memory.update(
                self._features(
                    index / 30.0,
                    energy=energy,
                    flux=energy,
                    stability=0.5,
                )
            )

        self.assertGreater(context.short_energy, context.medium_energy)
        self.assertGreater(context.energy_trend, 0.1)
        self.assertGreater(context.activity_trend, 0.05)
        self.assertGreater(context.tension, 0.3)

    def test_novel_onset_exceeds_repeated_onset(self):
        memory = MusicalMemory()
        for index in range(90):
            repeated = index % 10 == 0
            memory.update(
                self._features(
                    index / 30.0,
                    energy=0.3,
                    flux=0.4 if repeated else 0.05,
                    onset=repeated,
                    stability=0.9,
                )
            )

        repeated_context = memory.update(
            self._features(3.0, energy=0.3, flux=0.4, onset=True, stability=0.9)
        )
        novel_context = memory.update(
            self._features(
                3.0 + 1.0 / 30.0,
                energy=0.8,
                flux=1.0,
                onset=True,
                stability=0.1,
                centroid=0.8,
            )
        )

        self.assertGreater(novel_context.novelty, repeated_context.novelty)

    def test_silence_after_intensity_retains_persistence(self):
        memory = MusicalMemory()
        for index in range(90):
            memory.update(self._features(index / 30.0, energy=0.9, flux=0.5))

        context = memory.update(self._features(3.0, energy=0.0, flux=0.0))

        self.assertEqual(context.energy, 0.0)
        self.assertGreater(context.persistence, 0.5)

    @staticmethod
    def _features(
        timestamp,
        energy,
        flux=0.0,
        onset=False,
        stability=1.0,
        centroid=0.3,
    ):
        return AudioFeatures(
            timestamp=timestamp,
            amplitude=energy,
            bass=0.0,
            mid=0.0,
            treble=0.0,
            spectral_flux=flux,
            beat=onset,
            spectral_centroid=centroid,
            zero_crossing_rate=0.1,
            spectral_density=0.3,
            spectral_stability=stability,
        )


if __name__ == "__main__":
    unittest.main()
