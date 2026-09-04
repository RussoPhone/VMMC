"""Continuous vocal influence over the existing visual ecosystem."""

from dataclasses import dataclass


def _clamp(value):
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class VocalField:
    intensity: float = 0.0
    radius: float = 0.0
    roughness: float = 0.0
    continuity: float = 0.0
    pressure: float = 0.0

    @classmethod
    def silent(cls):
        return cls()


class VocalFieldController:
    def __init__(self):
        self._state = VocalField.silent()

    def update(self, context, dt):
        presence = _clamp(context.vocal_presence)
        activity = _clamp(context.vocal_activity)
        vocal_gate = _clamp(presence * 0.65 + activity * 0.35)
        targets = VocalField(
            intensity=_clamp(activity * 0.8 + presence * activity * 0.2),
            radius=_clamp(
                presence * 0.55
                + activity * 0.25
                + context.prominence * presence * 0.2
            ),
            roughness=_clamp(
                vocal_gate
                * (
                    context.signature.noisiness * 0.72
                    + context.signature.attack * 0.28
                )
            ),
            continuity=_clamp(
                presence
                * (context.signature_continuity * 0.7 + context.stability * 0.3)
            ),
            pressure=_clamp(
                activity
                * (
                    context.tension * 0.55
                    + context.regimes.building * 0.2
                    + context.regimes.climax * 0.25
                )
            ),
        )
        values = {}
        dt = max(0.0, dt)
        for name, target in vars(targets).items():
            current = getattr(self._state, name)
            rate = 5.0 if target > current else 1.15
            values[name] = current + (target - current) * min(1.0, dt * rate)
        self._state = VocalField(**values)
        return self._state
