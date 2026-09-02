import math
from dataclasses import dataclass


def _clamp(value):
    return max(0.0, min(1.0, value))


def _approach(current, target, attack, release, dt):
    rate = attack if target > current else release
    alpha = 1.0 - math.exp(-rate * dt)
    return _clamp(current + (target - current) * alpha)


@dataclass
class GestureState:
    pressure: float = 0.0
    release: float = 0.0
    impact: float = 0.0
    suspension: float = 0.0
    expansion: float = 0.0
    rupture: float = 0.0
    crescendo: float = 0.0
    lift: float = 0.0


class GestureEngine:
    def __init__(self):
        self.state = GestureState()
        self._pressure_reservoir = 0.0
        self._event_residue = 0.0
        self._onset_habituation = 1.0

    def update(self, context, dt: float) -> GestureState:
        dt = max(0.0, min(0.1, dt))
        growth = max(0.0, context.energy_trend)
        activity_growth = max(0.0, context.activity_trend)
        containment = max(0.0, context.short_energy - context.medium_energy)
        regimes = getattr(context, "regimes", None)
        building = getattr(regimes, "building", 0.0)
        climax = getattr(regimes, "climax", 0.0)
        contextual_release = getattr(regimes, "release", 0.0)
        signature = getattr(context, "signature", None)
        explosive_character = _clamp(
            getattr(signature, "attack", 0.0) * .6
            + getattr(signature, "noisiness", 0.0) * .4
        )
        crescendo_target = _clamp(
            building * (.55 + context.persistence * .35)
            + growth * .65
            + activity_growth * .25
        )
        pressure_target = _clamp(
            context.tension * 0.55
            + growth * 1.2
            + activity_growth * 0.8
            + containment * 0.4
            + crescendo_target * .45
        )
        pressure_rate = 1.6 if pressure_target > self._pressure_reservoir else 0.35
        pressure_alpha = 1.0 - math.exp(-pressure_rate * dt)
        self._pressure_reservoir += (
            pressure_target - self._pressure_reservoir
        ) * pressure_alpha

        onset_strength = 1.0 if context.onset else 0.0
        if context.onset:
            self._onset_habituation = max(0.25, self._onset_habituation * 0.86)
        else:
            self._onset_habituation += (1.0 - self._onset_habituation) * dt * 0.5

        impact_target = _clamp(
            onset_strength
            * (
                0.18
                + context.novelty * 0.55
                + self._pressure_reservoir * 0.35
            )
            * (1.0 - context.stability * 0.45)
            * self._onset_habituation
        )
        release_target = _clamp(
            self._pressure_reservoir
            * (
                context.novelty * 0.55
                + onset_strength * 0.35
                + climax * .9
                + contextual_release * .55
            )
            * (1.0 - growth * 0.6)
        )
        self._pressure_reservoir = _clamp(
            self._pressure_reservoir - release_target * dt * 2.4
        )

        rupture_target = _clamp(
            impact_target
            * (
                context.novelty * 0.45
                + context.zero_crossing_rate * 0.30
                + context.spectral_density * 0.25
            )
            + release_target * explosive_character * .45
        )
        expansion_target = _clamp(
            release_target * (.62 + context.energy * .22 + explosive_character * .38)
            + impact_target * context.energy * 0.15
        )
        lift_target = _clamp(
            self._pressure_reservoir
            * (.3 + crescendo_target * .7)
            * (1.0 - release_target * .8)
        )

        self._event_residue = max(
            self._event_residue * math.exp(-0.45 * dt),
            impact_target,
            self._pressure_reservoir * 0.7,
            context.tension * 0.5,
        )
        suspension_target = _clamp(
            (1.0 - context.energy) * context.persistence * self._event_residue
        )

        s = self.state
        s.pressure = _approach(
            s.pressure, self._pressure_reservoir, 4.0, 1.0, dt
        )
        s.release = _approach(s.release, release_target, 14.0, 4.0, dt)
        s.impact = _approach(s.impact, impact_target, 18.0, 8.0, dt)
        s.suspension = _approach(s.suspension, suspension_target, 8.0, 1.2, dt)
        s.expansion = _approach(s.expansion, expansion_target, 12.0, 3.0, dt)
        s.rupture = _approach(s.rupture, rupture_target, 16.0, 2.5, dt)
        s.crescendo = _approach(s.crescendo, crescendo_target, 2.2, .65, dt)
        s.lift = _approach(s.lift, lift_target, 2.8, 2.2, dt)
        return s
