import unittest
from types import SimpleNamespace

import main
from audio.input import PlaybackState
from memory.adaptive_landscape import RelativeFeatures
from memory.musical_memory import CyclePhase, RegimeWeights, SoundSignature


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
            relative=RelativeFeatures(0.2, -0.1, 0.3, 0.4, 0.9),
            signature=SoundSignature(0.6, 0.2, 0.8, 0.4, 0.5),
            signature_continuity=0.7,
            prominence=0.8,
            regimes=RegimeWeights(0.6, 0.4, 0.2, 0.3, 0.5, 0.1, 0.7),
            cycle_phase=CyclePhase.QUIETING,
            cycle_index=2,
            silence_duration=4.5,
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
        for heading in (
            "AUDIO",
            "CONTEXT",
            "LANDSCAPE",
            "SIGNATURE",
            "REGIME",
            "GESTURES",
            "MORPHOLOGY",
            "COLOR",
        ):
            self.assertIn(heading, text)
        self.assertIn("cycle=2", text)
        self.assertIn("silence=4.50", text)
        self.assertIn("prominence=0.80", text)

    def test_optional_ecology_receives_every_interpreted_frame(self):
        frames = [SimpleNamespace(frame_index=0), SimpleNamespace(frame_index=1)]
        audio = SimpleNamespace(get_next_frame=lambda: frames.pop(0) if frames else None)
        analyzer = SimpleNamespace(analyze=lambda frame: SimpleNamespace(timestamp=frame.frame_index/30, index=frame.frame_index))
        memory = SimpleNamespace(update=lambda features: SimpleNamespace(index=features.index, regimes=SimpleNamespace(stability=.6)))
        gestures = SimpleNamespace(update=lambda context, dt: SimpleNamespace(index=context.index))
        morphology = SimpleNamespace(update=lambda context, value, dt: SimpleNamespace(index=context.index))
        seen = []
        tracker = SimpleNamespace(update=lambda context, timestamp: (context.index,))
        ecosystem = SimpleNamespace(update=lambda presences, dt, global_cohesion: seen.append(presences) or SimpleNamespace(organisms=presences))

        result = main.drain_expressive_frames(audio, analyzer, memory, gestures, morphology, presence_tracker=tracker, ecosystem_controller=ecosystem)

        self.assertEqual(seen, [(0,), (1,)])
        self.assertEqual(result.ecosystem.organisms, (1,))


if __name__ == "__main__":
    unittest.main()
