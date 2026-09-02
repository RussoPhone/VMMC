import unittest
from types import SimpleNamespace

import vocal_main


class VocalPipelineTests(unittest.TestCase):
    def test_every_frame_crosses_only_analysis_memory_and_gate_in_order(self):
        calls = []
        frames = [SimpleNamespace(frame_index=0), SimpleNamespace(frame_index=1)]

        class Audio:
            def get_next_frame(self):
                return frames.pop(0) if frames else None

        class Analyzer:
            def analyze(self, frame):
                calls.append(("audio", frame.frame_index))
                return SimpleNamespace(index=frame.frame_index, timestamp=frame.frame_index / 30)

        class Memory:
            def update(self, features):
                calls.append(("memory", features.index))
                return SimpleNamespace(index=features.index)

        class Gate:
            def update(self, features, context, dt):
                calls.append(("gate", context.index))
                return SimpleNamespace(confirmed=True, open_amount=0.8)

        result = vocal_main.drain_vocal_frames(
            Audio(), Analyzer(), Memory(), Gate()
        )

        self.assertEqual(
            calls,
            [
                ("audio", 0),
                ("memory", 0),
                ("gate", 0),
                ("audio", 1),
                ("memory", 1),
                ("gate", 1),
            ],
        )
        self.assertEqual(result.features.index, 1)
        self.assertIs(result.audio_frame.frame_index, 1)

    def test_vocal_frame_has_no_instrumental_visual_state(self):
        fields = set(vocal_main.VocalFrame.__dataclass_fields__)

        self.assertEqual(fields, {"audio_frame", "features", "context", "gate"})
        self.assertTrue(fields.isdisjoint({"morphology", "presences", "ecosystem"}))


if __name__ == "__main__":
    unittest.main()
