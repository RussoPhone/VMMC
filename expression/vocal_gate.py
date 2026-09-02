"""Conservative, hysteretic gate for voice-only visual experiments."""

from dataclasses import dataclass


def _clamp(value):
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class VocalGateState:
    open_amount: float = 0.0
    confidence: float = 0.0
    confirmed: bool = False
    rejected_background: bool = False


class VocalGate:
    def __init__(self, confirm_seconds=0.35, open_threshold=0.68, close_threshold=0.42):
        self.confirm_seconds = confirm_seconds
        self.open_threshold = open_threshold
        self.close_threshold = close_threshold
        self._candidate_time = 0.0
        self._confirmed = False
        self._open_amount = 0.0

    def update(self, features, context, dt):
        dt = max(0.0, min(0.1, dt))
        confidence = _clamp(
            features.vocal_evidence * 0.38
            + features.vocal_intensity * 0.18
            + context.vocal_activity * 0.16
            + context.vocal_presence * 0.16
            + context.signature_continuity * 0.08
            + context.signature.harmonicity * 0.04
            - context.signature.noisiness * 0.10
        )
        if confidence >= self.open_threshold:
            self._candidate_time += dt
        else:
            self._candidate_time = max(0.0, self._candidate_time - dt * 2.0)
        if not self._confirmed and self._candidate_time + 1e-9 >= self.confirm_seconds:
            self._confirmed = True
        elif self._confirmed and confidence < self.close_threshold:
            self._confirmed = False

        target = confidence if self._confirmed else 0.0
        rate = 4.0 if target > self._open_amount else 1.2
        self._open_amount += (
            target - self._open_amount
        ) * min(1.0, dt * rate)
        rejected = not self._confirmed and features.amplitude > 0.05
        return VocalGateState(
            _clamp(self._open_amount),
            confidence,
            self._confirmed,
            rejected,
        )
