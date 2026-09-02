import unittest

from expression.gesture_engine import GestureEngine
from memory.musical_memory import MusicalContext, RegimeWeights, SoundSignature


class GestureEngineTests(unittest.TestCase):
    def test_crescendo_builds_more_pressure_than_stable_energy(self):
        stable = GestureEngine()
        crescendo = GestureEngine()
        for index in range(90):
            stable_state = stable.update(
                self._context(energy=0.8, short=0.8, medium=0.8, stability=0.9),
                1.0 / 30.0,
            )
            crescendo_state = crescendo.update(
                self._context(
                    energy=0.2 + index / 150.0,
                    short=0.5,
                    medium=0.25,
                    trend=0.25,
                    activity_trend=0.2,
                    tension=0.8,
                    stability=0.35,
                ),
                1.0 / 30.0,
            )

        self.assertGreater(crescendo_state.pressure, stable_state.pressure + 0.2)

    def test_drop_releases_more_after_crescendo_than_in_isolation(self):
        prepared = GestureEngine()
        isolated = GestureEngine()
        for _ in range(90):
            prepared.update(
                self._context(
                    energy=0.7,
                    short=0.6,
                    medium=0.3,
                    trend=0.3,
                    activity_trend=0.2,
                    tension=0.9,
                    stability=0.3,
                ),
                1.0 / 30.0,
            )

        drop = self._context(
            energy=0.9,
            short=0.7,
            medium=0.5,
            novelty=0.9,
            tension=0.4,
            onset=True,
            stability=0.15,
        )
        prepared_drop = prepared.update(drop, 1.0 / 30.0)
        isolated_drop = isolated.update(drop, 1.0 / 30.0)

        self.assertGreater(prepared_drop.release, isolated_drop.release + 0.1)
        self.assertGreater(prepared_drop.expansion, isolated_drop.expansion + 0.05)

    def test_silence_after_intensity_creates_suspension(self):
        engine = GestureEngine()
        for _ in range(30):
            engine.update(
                self._context(energy=0.9, tension=0.8, persistence=0.9),
                1.0 / 30.0,
            )

        state = engine.update(
            self._context(energy=0.02, persistence=0.85, stability=0.7),
            1.0 / 30.0,
        )

        self.assertGreater(state.suspension, 0.1)

    def test_repeated_onsets_lose_impact(self):
        engine = GestureEngine()
        impacts = []
        for index in range(12):
            state = engine.update(
                self._context(
                    energy=0.5,
                    novelty=max(0.05, 0.6 - index * 0.05),
                    onset=True,
                    stability=min(0.95, 0.4 + index * 0.05),
                ),
                0.1,
            )
            impacts.append(state.impact)

        self.assertGreater(max(impacts[:3]), max(impacts[-3:]))

    def test_crescendo_compresses_and_lifts_before_climax_release(self):
        engine = GestureEngine()
        for _ in range(90):
            building = engine.update(
                self._context(
                    energy=.55,
                    trend=.28,
                    tension=.85,
                    persistence=.8,
                    building=.9,
                ),
                1 / 30,
            )

        self.assertGreater(building.pressure, .55)
        self.assertGreater(building.lift, .35)
        climax = engine.update(
            self._context(
                energy=.9,
                tension=.9,
                persistence=.9,
                onset=True,
                climax=.95,
                attack=.9,
                noise=.7,
            ),
            .1,
        )
        self.assertGreater(climax.expansion, .25)
        self.assertGreater(climax.rupture, .05)

    @staticmethod
    def _context(
        energy=0.4,
        short=0.4,
        medium=0.4,
        trend=0.0,
        activity=0.3,
        activity_trend=0.0,
        novelty=0.05,
        stability=0.8,
        tension=0.2,
        persistence=0.4,
        onset=False,
        centroid=0.3,
        zcr=0.1,
        density=0.3,
        building=0.0,
        climax=0.0,
        release=0.0,
        attack=0.0,
        noise=0.0,
    ):
        return MusicalContext(
            energy=energy,
            short_energy=short,
            medium_energy=medium,
            energy_trend=trend,
            activity=activity,
            activity_trend=activity_trend,
            novelty=novelty,
            stability=stability,
            tension=tension,
            persistence=persistence,
            spectral_centroid=centroid,
            zero_crossing_rate=zcr,
            spectral_density=density,
            onset=onset,
            regimes=RegimeWeights(.5, building, 0.0, 0.0, climax, release, 0.0),
            signature=SoundSignature(centroid, noise, 1-noise, attack, density),
        )


if __name__ == "__main__":
    unittest.main()
