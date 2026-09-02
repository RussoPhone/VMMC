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

    def test_returning_signature_recovers_continuity(self):
        memory = MusicalMemory()
        for index in range(60):
            memory.update(
                self._features(
                    index / 30.0,
                    energy=0.3,
                    centroid=0.2,
                    flatness=0.1,
                    harmonicity=0.9,
                    density=0.2,
                )
            )

        contrasting = memory.update(
            self._features(
                2.0,
                energy=0.3,
                centroid=0.8,
                flatness=0.8,
                harmonicity=0.2,
                density=0.8,
            )
        )
        returned = memory.update(
            self._features(
                2.0 + 1.0 / 30.0,
                energy=0.3,
                centroid=0.2,
                flatness=0.1,
                harmonicity=0.9,
                density=0.2,
            )
        )

        self.assertLess(contrasting.signature_continuity, 0.5)
        self.assertGreater(
            returned.signature_continuity,
            contrasting.signature_continuity + 0.3,
        )

    def test_subtle_event_is_more_prominent_in_calm_music(self):
        calm = MusicalMemory()
        intense = MusicalMemory()
        for index in range(180):
            timestamp = index / 30.0
            calm.update(self._features(timestamp, energy=0.03, centroid=0.2))
            intense.update(self._features(timestamp, energy=0.7, centroid=0.7))

        detail = self._features(
            6.0,
            energy=0.18,
            flux=0.2,
            centroid=0.5,
            attack=0.3,
        )
        calm_context = calm.update(detail)
        intense_context = intense.update(detail)

        self.assertGreater(calm_context.prominence, 0.55)
        self.assertGreater(
            calm_context.prominence, intense_context.prominence + 0.25
        )

    def test_uncertain_signature_still_has_finite_expressive_output(self):
        context = MusicalMemory().update(self._features(0.0, energy=0.0))

        self.assertGreaterEqual(context.prominence, 0.0)
        self.assertLessEqual(context.prominence, 1.0)
        for value in vars(context.signature).values():
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    @staticmethod
    def _features(
        timestamp,
        energy,
        flux=0.0,
        onset=False,
        stability=1.0,
        centroid=0.3,
        flatness=0.0,
        harmonicity=0.0,
        density=0.3,
        attack=0.0,
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
            spectral_density=density,
            spectral_stability=stability,
            spectral_flatness=flatness,
            harmonicity=harmonicity,
            attack_strength=attack,
        )


if __name__ == "__main__":
    unittest.main()
