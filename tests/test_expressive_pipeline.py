import unittest
from types import SimpleNamespace

import main
from audio.input import PlaybackState


class ExpressivePipelineTests(unittest.TestCase):
    def test_every_elapsed_frame_crosses_all_contextual_layers_in_order(self):
        calls = []
        frames = [SimpleNamespace(frame_index=0), SimpleNamespace(frame_index=1)]

        class Audio:
            def get_next_frame(self):
                return frames.pop(0) if frames else None

        class Analyzer:
            def analyze(self, frame):
                calls.append(("audio", frame.frame_index))
                return SimpleNamespace(timestamp=frame.frame_index / 30.0, index=frame.frame_index)

        class Memory:
            def update(self, features):
                calls.append(("memory", features.index))
                return SimpleNamespace(index=features.index)

        class Gestures:
            def update(self, context, dt):
                calls.append(("gesture", context.index))
                return SimpleNamespace(index=context.index)

        class Morphology:
            def update(self, context, gestures, dt):
                calls.append(("morphology", gestures.index))
                return SimpleNamespace(index=gestures.index)

        result = main.drain_expressive_frames(
            Audio(), Analyzer(), Memory(), Gestures(), Morphology()
        )

        self.assertEqual(
            calls,
            [
                ("audio", 0),
                ("memory", 0),
                ("gesture", 0),
                ("morphology", 0),
                ("audio", 1),
                ("memory", 1),
                ("gesture", 1),
                ("morphology", 1),
            ],
        )
        self.assertEqual(result.features.index, 1)
        self.assertEqual(result.morphology.index, 1)

    def test_debug_output_exposes_each_pipeline_layer(self):
        features = SimpleNamespace(
            amplitude=0.5,
            bass=0.4,
            mid=0.3,
            treble=0.2,
            spectral_flux=0.1,
            beat=True,
            spectral_centroid=0.6,
            zero_crossing_rate=0.2,
            spectral_density=0.5,
        )
        context = SimpleNamespace(
            short_energy=0.45,
            medium_energy=0.35,
            energy_trend=0.1,
            novelty=0.4,
            stability=0.7,
            tension=0.8,
            activity=0.5,
            persistence=0.6,
        )
        gestures = SimpleNamespace(
            pressure=0.8,
            release=0.2,
            impact=0.6,
            suspension=0.1,
            expansion=0.4,
            rupture=0.3,
        )
        morphology = SimpleNamespace(
            wave=0.7,
            mass=0.5,
            shard=0.3,
            noise=0.2,
            roughness=0.4,
            elasticity=0.6,
            fluidity=0.7,
            symmetry=0.8,
            hue=0.55,
            saturation=0.65,
            brightness=0.75,
            color_stability=0.85,
        )
        audio = SimpleNamespace(state=PlaybackState.PLAYING)

        lines = main._build_debug_lines(
            features,
            context,
            gestures,
            morphology,
            "/tmp/song.wav",
            audio,
        )

        text = "\n".join(lines)
        for heading in ("AUDIO", "CONTEXT", "GESTURES", "MORPHOLOGY", "COLOR"):
            self.assertIn(heading, text)


if __name__ == "__main__":
    unittest.main()
