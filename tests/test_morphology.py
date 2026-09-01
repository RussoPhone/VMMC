import unittest

from expression.gesture_engine import GestureState
from memory.musical_memory import MusicalContext
from state.morphology import MorphologyController, MorphologyState


class MorphologyTests(unittest.TestCase):
    def test_default_morphology_is_neutral_and_normalized(self):
        state = MorphologyState()

        for name, value in vars(state).items():
            if name != "rotation":
                self.assertGreaterEqual(value, 0.0, name)
                self.assertLessEqual(value, 1.0, name)
        self.assertGreater(state.symmetry, 0.8)
        self.assertLess(state.fragmentation, 0.1)

    def test_stable_smooth_spectrum_favors_wave_and_fluidity(self):
        controller = MorphologyController()
        context = self._context(stability=0.95, centroid=0.2, zcr=0.02, density=0.3)
        gestures = GestureState()

        for _ in range(60):
            state = controller.update(context, gestures, 1.0 / 30.0)

        self.assertGreater(state.wave, state.shard)
        self.assertGreater(state.fluidity, state.roughness)

    def test_bright_rough_rupture_creates_shards_and_fragmentation(self):
        controller = MorphologyController()
        context = self._context(
            stability=0.1,
            centroid=0.85,
            zcr=0.8,
            density=0.75,
            novelty=0.9,
            tension=0.8,
        )
        gestures = GestureState(impact=0.8, rupture=0.9, pressure=0.5)

        for _ in range(45):
            state = controller.update(context, gestures, 1.0 / 30.0)

        self.assertGreater(state.shard, 0.5)
        self.assertGreater(state.roughness, 0.5)
        self.assertGreater(state.fragmentation, 0.4)
        self.assertLess(state.symmetry, 0.7)

    def test_pressure_compresses_before_release_expands(self):
        controller = MorphologyController()
        context = self._context(tension=0.8, stability=0.4)
        for _ in range(45):
            compressed = controller.update(
                context,
                GestureState(pressure=0.9),
                1.0 / 30.0,
            )
        compression_before_release = compressed.compression

        for _ in range(20):
            expanded = controller.update(
                context,
                GestureState(release=0.9, expansion=0.9),
                1.0 / 30.0,
            )

        self.assertGreater(compression_before_release, 0.5)
        self.assertGreater(expanded.expansion, expanded.compression)

    def test_roughness_leaves_a_slow_residue(self):
        controller = MorphologyController()
        rough = self._context(stability=0.1, centroid=0.9, zcr=0.9, novelty=0.9)
        for _ in range(30):
            controller.update(rough, GestureState(rupture=0.9), 1.0 / 30.0)

        before = controller.state.residue
        calm = self._context(energy=0.05, stability=1.0, centroid=0.1, zcr=0.0)
        after = controller.update(calm, GestureState(), 1.0 / 30.0).residue

        self.assertGreater(before, 0.2)
        self.assertGreater(after, 0.0)
        self.assertLess(after, before)

    @staticmethod
    def _context(
        energy=0.4,
        stability=0.7,
        centroid=0.3,
        zcr=0.1,
        density=0.3,
        novelty=0.05,
        tension=0.2,
    ):
        return MusicalContext(
            energy=energy,
            short_energy=energy,
            medium_energy=energy,
            energy_trend=0.0,
            activity=0.3,
            activity_trend=0.0,
            novelty=novelty,
            stability=stability,
            tension=tension,
            persistence=energy,
            spectral_centroid=centroid,
            zero_crossing_rate=zcr,
            spectral_density=density,
            onset=False,
        )


if __name__ == "__main__":
    unittest.main()
