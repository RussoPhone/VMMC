import unittest

from audio.analyzer import AudioFeatures
from memory.musical_memory import CyclePhase, MusicalMemory


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

    def test_prepared_crescendo_builds_more_than_isolated_spike(self):
        prepared_memory = MusicalMemory()
        isolated_memory = MusicalMemory()
        prepared = None
        for index in range(180):
            timestamp = index / 30.0
            energy = 0.1 + 0.7 * index / 179
            prepared = prepared_memory.update(
                self._features(
                    timestamp,
                    energy=energy,
                    flux=energy * 0.5,
                    stability=0.7,
                )
            )
            isolated_energy = 0.8 if index == 179 else 0.1
            isolated = isolated_memory.update(
                self._features(
                    timestamp,
                    energy=isolated_energy,
                    flux=0.4 if index == 179 else 0.02,
                    stability=0.7,
                )
            )

        self.assertGreater(
            prepared.regimes.building, isolated.regimes.building + 0.2
        )
        self.assertGreater(prepared.tension, isolated.tension)

    def test_timbre_break_creates_rupture_and_transition(self):
        stable_memory = MusicalMemory()
        breaking_memory = MusicalMemory()
        for index in range(120):
            sample = self._features(
                index / 30.0,
                energy=0.3,
                centroid=0.2,
                flatness=0.1,
                harmonicity=0.9,
                stability=0.95,
            )
            stable_memory.update(sample)
            breaking_memory.update(sample)

        stable = stable_memory.update(
            self._features(
                4.0,
                energy=0.3,
                centroid=0.2,
                flatness=0.1,
                harmonicity=0.9,
                stability=0.95,
            )
        )
        broken = breaking_memory.update(
            self._features(
                4.0,
                energy=0.8,
                flux=0.9,
                centroid=0.9,
                flatness=0.9,
                harmonicity=0.1,
                density=0.9,
                attack=0.8,
                stability=0.1,
            )
        )

        self.assertGreater(broken.regimes.rupture, stable.regimes.rupture + 0.3)
        self.assertGreater(
            broken.regimes.transition, stable.regimes.transition + 0.3
        )

    def test_release_grows_after_tension_falls(self):
        memory = MusicalMemory()
        for index in range(120):
            energy = 0.2 + 0.7 * index / 119
            memory.update(
                self._features(
                    index / 30.0,
                    energy=energy,
                    flux=energy,
                    stability=0.5,
                )
            )

        first_release = None
        final = None
        for index in range(45):
            final = memory.update(
                self._features(
                    4.0 + index / 30.0,
                    energy=0.05,
                    flux=0.0,
                    stability=0.95,
                )
            )
            if first_release is None:
                first_release = final

        self.assertGreater(final.regimes.release, first_release.regimes.release)
        self.assertLess(final.regimes.climax, first_release.regimes.climax)

    def test_twelve_seconds_of_silence_end_the_cycle_exactly(self):
        memory = MusicalMemory()
        for index in range(90):
            memory.update(self._features(index / 30.0, energy=0.4, flux=0.1))

        memory.update(self._features(3.0, energy=0.0, flux=0.0))
        before = memory.update(self._features(14.99, energy=0.0, flux=0.0))
        boundary = memory.update(self._features(15.0, energy=0.0, flux=0.0))

        self.assertEqual(before.cycle_phase, CyclePhase.QUIETING)
        self.assertAlmostEqual(before.silence_duration, 11.99, places=2)
        self.assertEqual(boundary.cycle_phase, CyclePhase.ENDED)
        self.assertAlmostEqual(boundary.silence_duration, 12.0, places=6)

    def test_low_noise_does_not_restart_silence_timer(self):
        memory = MusicalMemory()
        for index in range(90):
            memory.update(self._features(index / 30.0, energy=0.4, flux=0.1))

        memory.update(self._features(3.0, energy=0.0, flux=0.0))
        memory.update(self._features(9.0, energy=0.005, flux=0.0))
        ended = memory.update(self._features(15.0, energy=0.005, flux=0.0))

        self.assertEqual(ended.cycle_phase, CyclePhase.ENDED)
        self.assertEqual(ended.cycle_index, 0)

    def test_contextual_silence_threshold_does_not_decay_during_quieting(self):
        memory = MusicalMemory()
        for index in range(180):
            memory.update(self._features(index / 30.0, energy=0.4, flux=0.1))

        quieting = None
        for index in range(361):
            quieting = memory.update(
                self._features(6.0 + index / 30.0, energy=0.011, flux=0.0)
            )

        self.assertEqual(quieting.cycle_phase, CyclePhase.ENDED)
        self.assertAlmostEqual(quieting.silence_duration, 12.0, places=6)

    def test_real_sound_after_ended_cycle_starts_fresh_landscape(self):
        memory = MusicalMemory()
        for index in range(90):
            memory.update(
                self._features(
                    index / 30.0,
                    energy=0.4,
                    centroid=0.2,
                    harmonicity=0.9,
                )
            )
        memory.update(self._features(3.0, energy=0.0, flux=0.0))
        memory.update(self._features(15.0, energy=0.0, flux=0.0))

        restarted = memory.update(
            self._features(
                15.1,
                energy=0.5,
                flux=0.2,
                centroid=0.8,
                flatness=0.7,
            )
        )

        self.assertEqual(restarted.cycle_phase, CyclePhase.LISTENING)
        self.assertEqual(restarted.cycle_index, 1)
        self.assertLess(restarted.relative.confidence, 0.01)
        self.assertEqual(restarted.signature_continuity, 0.0)

    def test_continuous_timbre_transition_stays_in_same_cycle(self):
        memory = MusicalMemory()
        for index in range(120):
            memory.update(
                self._features(
                    index / 30.0,
                    energy=0.3,
                    centroid=0.2,
                    harmonicity=0.9,
                )
            )

        transitioned = memory.update(
            self._features(
                4.0,
                energy=0.8,
                flux=0.9,
                centroid=0.9,
                flatness=0.9,
                harmonicity=0.1,
                attack=0.8,
            )
        )

        self.assertEqual(transitioned.cycle_phase, CyclePhase.LISTENING)
        self.assertEqual(transitioned.cycle_index, 0)
        self.assertGreater(transitioned.regimes.transition, 0.2)

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
