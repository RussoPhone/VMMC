import unittest
from types import SimpleNamespace

import numpy as np

from renderer.vocal_renderer import VocalTrace


def vocal_frame(open_amount, *, rejected=False, sample_value=0.4):
    return SimpleNamespace(
        audio_frame=SimpleNamespace(samples=np.full(64, sample_value)),
        features=SimpleNamespace(vocal_evidence=0.8, vocal_intensity=0.7),
        context=SimpleNamespace(
            vocal_activity=0.65,
            vocal_presence=0.75,
            tension=0.5,
            signature_continuity=0.8,
            signature=SimpleNamespace(noisiness=0.25),
        ),
        gate=SimpleNamespace(
            open_amount=open_amount,
            confidence=0.72,
            confirmed=open_amount > 0.0,
            rejected_background=rejected,
        ),
    )


class VocalTraceTests(unittest.TestCase):
    def test_rejected_background_adds_diagnostics_but_no_expressive_wave(self):
        trace = VocalTrace(max_history=8)

        trace.record(vocal_frame(0.0, rejected=True))

        self.assertEqual(len(trace.waveforms), 0)
        self.assertEqual(trace.history["confidence"][-1], 0.72)
        self.assertEqual(trace.rejected_count, 1)

    def test_accepted_voice_adds_wave_and_all_parameter_histories(self):
        trace = VocalTrace(max_history=8)

        trace.record(vocal_frame(0.75))

        self.assertEqual(len(trace.waveforms), 1)
        self.assertEqual(
            set(trace.history),
            {"evidence", "intensity", "pressure", "continuity", "roughness", "confidence"},
        )
        self.assertTrue(all(len(values) == 1 for values in trace.history.values()))

    def test_histories_remain_bounded(self):
        trace = VocalTrace(max_history=5)

        for _ in range(12):
            trace.record(vocal_frame(0.8))

        self.assertTrue(all(len(values) == 5 for values in trace.history.values()))
        self.assertEqual(len(trace.waveforms), 5)


if __name__ == "__main__":
    unittest.main()
