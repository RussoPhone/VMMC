import unittest
from types import SimpleNamespace

from expression.vocal_gate import VocalGate


def frame(evidence, intensity, *, amplitude=0.5, flatness=0.08):
    return SimpleNamespace(
        vocal_evidence=evidence,
        vocal_intensity=intensity,
        amplitude=amplitude,
        spectral_flatness=flatness,
    )


def context(activity, presence, *, continuity=0.85, harmonicity=0.9):
    return SimpleNamespace(
        vocal_activity=activity,
        vocal_presence=presence,
        signature_continuity=continuity,
        signature=SimpleNamespace(harmonicity=harmonicity, noisiness=0.08),
    )


class VocalGateTests(unittest.TestCase):
    def test_sustained_strong_voice_opens_only_after_confirmation(self):
        gate = VocalGate(confirm_seconds=0.3)

        early = gate.update(frame(0.92, 0.85), context(0.8, 0.9), 0.1)
        middle = gate.update(frame(0.92, 0.85), context(0.8, 0.9), 0.1)
        opened = gate.update(frame(0.92, 0.85), context(0.8, 0.9), 0.1)

        self.assertFalse(early.confirmed)
        self.assertFalse(middle.confirmed)
        self.assertTrue(opened.confirmed)
        self.assertGreater(opened.open_amount, 0.0)

    def test_instrument_like_harmonic_signal_stays_rejected(self):
        gate = VocalGate(confirm_seconds=0.3)

        for _ in range(20):
            state = gate.update(
                frame(0.62, 0.08, amplitude=0.7, flatness=0.03),
                context(0.06, 0.18, continuity=0.95, harmonicity=0.98),
                0.1,
            )

        self.assertFalse(state.confirmed)
        self.assertLess(state.open_amount, 0.05)
        self.assertTrue(state.rejected_background)

    def test_absence_closes_with_a_visible_decay(self):
        gate = VocalGate(confirm_seconds=0.2)
        for _ in range(10):
            active = gate.update(frame(0.95, 0.9), context(0.9, 0.95), 0.1)

        first_quiet = gate.update(
            frame(0.0, 0.0, amplitude=0.0, flatness=1.0),
            context(0.0, 0.0, continuity=0.0, harmonicity=0.0),
            0.1,
        )

        self.assertGreater(first_quiet.open_amount, 0.0)
        self.assertLess(first_quiet.open_amount, active.open_amount)
        quiet = first_quiet
        for _ in range(80):
            quiet = gate.update(
                frame(0.0, 0.0, amplitude=0.0, flatness=1.0),
                context(0.0, 0.0, continuity=0.0, harmonicity=0.0),
                0.1,
            )
        self.assertLess(quiet.open_amount, 0.01)


if __name__ == "__main__":
    unittest.main()
