import math
import unittest

import numpy as np

from audio.analyzer import AudioAnalyzer, AudioFeatures
from audio.input import AudioFrame
from memory.musical_memory import MusicalMemory
from state.visual_state import VisualStateController


class ContextualPipelineTests(unittest.TestCase):
    def test_analyzer_outputs_are_finite_and_normalized(self):
        samplerate = 48_000
        sample_count = 1_600
        times = np.arange(sample_count) / samplerate
        frames = [
            AudioFrame(np.zeros(sample_count), 0.0, samplerate, 0),
            AudioFrame(
                np.sin(2.0 * np.pi * 440.0 * times).astype(np.float32) * 0.2,
                1.0 / 30.0,
                samplerate,
                1,
            ),
        ]
        analyzer = AudioAnalyzer()

        for frame in frames:
            features = analyzer.analyze(frame)
            for value in (
                features.amplitude,
                features.bass,
                features.mid,
                features.treble,
                features.spectral_flux,
            ):
                self.assertTrue(math.isfinite(value))
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)

    def test_same_instant_has_different_context_after_different_histories(self):
        calm_memory = MusicalMemory()
        intense_memory = MusicalMemory()

        for index in range(90):
            timestamp = index / 30.0
            calm_memory.update(self._features(timestamp, amplitude=0.05))
            intense_memory.update(self._features(timestamp, amplitude=0.8))

        final = self._features(3.0, amplitude=0.8, spectral_flux=0.2)
        calm_context = calm_memory.update(final)
        intense_context = intense_memory.update(final)

        self.assertAlmostEqual(calm_context.energy, intense_context.energy)
        self.assertLess(calm_context.energy_average, intense_context.energy_average)
        self.assertGreater(calm_context.energy_trend, intense_context.energy_trend)
        self.assertGreater(calm_context.tension, intense_context.tension)

    def test_different_histories_create_distinct_continuous_visual_states(self):
        calm_memory = MusicalMemory()
        intense_memory = MusicalMemory()
        for index in range(90):
            timestamp = index / 30.0
            calm_memory.update(self._features(timestamp, amplitude=0.05))
            intense_memory.update(self._features(timestamp, amplitude=0.8))

        final = self._features(3.0, amplitude=0.8, spectral_flux=0.2)
        contexts = (calm_memory.update(final), intense_memory.update(final))
        controllers = (VisualStateController(), VisualStateController())

        for _ in range(30):
            for controller, context in zip(controllers, contexts):
                controller.update(context, 1.0 / 30.0)

        calm_state, intense_state = (controller.state for controller in controllers)
        self.assertNotAlmostEqual(calm_state.deformation, intense_state.deformation)

        previous_scale = calm_state.scale
        updated_scale = controllers[0].update(contexts[0], 1.0 / 30.0).scale
        target_scale = 1.0 + contexts[0].energy * 0.6 + contexts[0].energy_trend * 0.4
        self.assertGreater(updated_scale, previous_scale)
        self.assertLess(updated_scale, target_scale)

    @staticmethod
    def _features(timestamp, amplitude, spectral_flux=0.0):
        return AudioFeatures(
            timestamp=timestamp,
            amplitude=amplitude,
            bass=0.0,
            mid=0.0,
            treble=0.0,
            spectral_flux=spectral_flux,
            beat=False,
        )


if __name__ == "__main__":
    unittest.main()
