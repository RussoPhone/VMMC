import math
import unittest

import numpy as np

from audio.analyzer import AudioAnalyzer, AudioFeatures
from audio.input import AudioFrame
from expression.gesture_engine import GestureEngine
from memory.musical_memory import MusicalMemory
from state.morphology import MorphologyController


class ContextualPipelineTests(unittest.TestCase):
    def test_spectral_centroid_distinguishes_low_and_high_tones(self):
        low = self._analyze_tone(100.0)
        high = self._analyze_tone(4_000.0)

        self.assertGreater(high.spectral_centroid, low.spectral_centroid + 0.1)

    def test_zero_crossing_rate_distinguishes_noise_from_tone(self):
        samplerate = 48_000
        count = 1_600
        tone = np.sin(2.0 * np.pi * 440.0 * np.arange(count) / samplerate)
        alternating = np.tile([-0.2, 0.2], count // 2)
        analyzer = AudioAnalyzer()

        tone_features = analyzer.analyze(AudioFrame(tone, 0.0, samplerate, 0))
        noise_features = analyzer.analyze(
            AudioFrame(alternating, 1.0 / 30.0, samplerate, 1)
        )

        self.assertGreater(
            noise_features.zero_crossing_rate,
            tone_features.zero_crossing_rate + 0.5,
        )

    def test_identical_consecutive_spectra_are_stable(self):
        samplerate = 48_000
        count = 1_600
        samples = np.sin(2.0 * np.pi * 440.0 * np.arange(count) / samplerate)
        analyzer = AudioAnalyzer()
        analyzer.analyze(AudioFrame(samples, 0.0, samplerate, 0))

        features = analyzer.analyze(
            AudioFrame(samples.copy(), 1.0 / 30.0, samplerate, 1)
        )

        self.assertGreater(features.spectral_stability, 0.95)
        self.assertGreaterEqual(features.spectral_density, 0.0)
        self.assertLessEqual(features.spectral_density, 1.0)

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
                features.spectral_flatness,
                features.harmonicity,
                features.attack_strength,
                features.spectral_spread,
            ):
                self.assertTrue(math.isfinite(value))
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)

    def test_tone_is_more_harmonic_and_less_flat_than_seeded_noise(self):
        samplerate = 48_000
        count = 1_600
        times = np.arange(count) / samplerate
        tone = 0.2 * np.sin(2.0 * np.pi * 440.0 * times)
        noise = np.random.default_rng(7).normal(0.0, 0.2, count)

        tone_features = AudioAnalyzer().analyze(
            AudioFrame(tone, 0.0, samplerate, 0)
        )
        noise_features = AudioAnalyzer().analyze(
            AudioFrame(noise, 0.0, samplerate, 0)
        )

        self.assertGreater(
            tone_features.harmonicity, noise_features.harmonicity + 0.25
        )
        self.assertLess(
            tone_features.spectral_flatness,
            noise_features.spectral_flatness - 0.25,
        )
        self.assertLess(
            tone_features.spectral_spread,
            noise_features.spectral_spread - 0.1,
        )

    def test_sudden_rise_has_more_attack_than_steady_level(self):
        analyzer = AudioAnalyzer()

        analyzer.analyze(self._tone_frame(0.02, 0.0, 0))
        attack = analyzer.analyze(self._tone_frame(0.4, 1.0 / 30.0, 1))
        sustained = analyzer.analyze(self._tone_frame(0.4, 2.0 / 30.0, 2))

        self.assertGreater(
            attack.attack_strength, sustained.attack_strength + 0.4
        )

    def test_cqt_resolves_note_bins_across_several_octaves(self):
        features = self._analyze_tone(440.0)

        self.assertGreaterEqual(len(features.cqt_notes), 72)
        peak = int(np.argmax(features.cqt_notes))
        peak_frequency = features.cqt_frequencies[peak]
        self.assertLess(abs(peak_frequency - 440.0), 30.0)

    def test_subtle_high_note_creates_local_treble_novelty(self):
        analyzer = AudioAnalyzer()
        samplerate = 48_000
        count = 1_600
        for index in range(30):
            analyzer.analyze(AudioFrame(np.zeros(count), index / 30, samplerate, index))

        times = np.arange(count) / samplerate
        subtle = .015 * np.sin(2 * np.pi * 5_000 * times)
        detected = analyzer.analyze(AudioFrame(subtle, 1.0, samplerate, 30))

        self.assertGreater(detected.local_novelty[2], .25)
        self.assertGreater(detected.local_novelty[2], detected.local_novelty[0] + .2)

    def test_local_novelty_adapts_to_sustained_note_in_its_own_region(self):
        analyzer = AudioAnalyzer()
        samplerate = 48_000
        count = 1_600
        times = np.arange(count) / samplerate
        tone = .02 * np.sin(2 * np.pi * 5_000 * times)
        first = analyzer.analyze(AudioFrame(tone, 0.0, samplerate, 0))
        latest = first
        for index in range(1, 60):
            latest = analyzer.analyze(
                AudioFrame(tone, index / 30, samplerate, index)
            )

        self.assertGreater(first.local_novelty[2], latest.local_novelty[2] + .15)

    def test_harmonic_voice_like_signal_exceeds_noise_vocal_evidence(self):
        samplerate = 48_000
        count = 1_600
        times = np.arange(count) / samplerate
        voiced = sum(
            (1 / harmonic)
            * np.sin(2 * np.pi * 180 * harmonic * times)
            for harmonic in range(1, 13)
        ) * .08
        noise = np.random.default_rng(11).normal(0, .08, count)

        voiced_features = AudioAnalyzer().analyze(
            AudioFrame(voiced, 0.0, samplerate, 0)
        )
        noise_features = AudioAnalyzer().analyze(
            AudioFrame(noise, 0.0, samplerate, 0)
        )

        self.assertGreater(
            voiced_features.vocal_evidence,
            noise_features.vocal_evidence + .2,
        )
        self.assertGreater(voiced_features.vocal_intensity, .05)

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

    def test_different_histories_create_distinct_continuous_morphologies(self):
        calm_memory = MusicalMemory()
        intense_memory = MusicalMemory()
        for index in range(90):
            timestamp = index / 30.0
            calm_memory.update(self._features(timestamp, amplitude=0.05))
            intense_memory.update(self._features(timestamp, amplitude=0.8))

        final = self._features(3.0, amplitude=0.8, spectral_flux=0.2)
        contexts = (calm_memory.update(final), intense_memory.update(final))
        gesture_engines = (GestureEngine(), GestureEngine())
        controllers = (MorphologyController(), MorphologyController())

        for _ in range(30):
            for gesture_engine, controller, context in zip(
                gesture_engines, controllers, contexts
            ):
                gestures = gesture_engine.update(context, 1.0 / 30.0)
                controller.update(context, gestures, 1.0 / 30.0)

        calm_state, intense_state = (controller.state for controller in controllers)
        self.assertNotAlmostEqual(calm_state.compression, intense_state.compression)

        previous_compression = calm_state.compression
        gestures = gesture_engines[0].update(contexts[0], 1.0 / 30.0)
        updated = controllers[0].update(contexts[0], gestures, 1.0 / 30.0)
        self.assertLess(abs(updated.compression - previous_compression), 0.1)

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

    @staticmethod
    def _analyze_tone(frequency):
        samplerate = 48_000
        count = 1_600
        samples = np.sin(2.0 * np.pi * frequency * np.arange(count) / samplerate)
        return AudioAnalyzer().analyze(AudioFrame(samples, 0.0, samplerate, 0))

    @staticmethod
    def _tone_frame(amplitude, timestamp, frame_index):
        samplerate = 48_000
        count = 1_600
        samples = amplitude * np.sin(
            2.0 * np.pi * 440.0 * np.arange(count) / samplerate
        )
        return AudioFrame(samples, timestamp, samplerate, frame_index)


if __name__ == "__main__":
    unittest.main()
