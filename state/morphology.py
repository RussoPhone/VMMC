import math
from dataclasses import dataclass


def _clamp(value):
    return max(0.0, min(1.0, value))


def _approach(current, target, attack, release, dt):
    rate = attack if target > current else release
    alpha = 1.0 - math.exp(-rate * dt)
    return _clamp(current + (target - current) * alpha)


@dataclass
class MorphologyState:
    wave: float = 0.35
    mass: float = 0.35
    shard: float = 0.05
    noise: float = 0.05
    roughness: float = 0.05
    elasticity: float = 0.5
    symmetry: float = 1.0
    density: float = 0.3
    fluidity: float = 0.5
    expansion: float = 0.0
    compression: float = 0.0
    rotation: float = 0.0
    brightness: float = 0.25
    saturation: float = 0.25
    hue: float = 0.55
    color_stability: float = 1.0
    fragmentation: float = 0.0
    residue: float = 0.0


class MorphologyController:
    def __init__(self):
        self.state = MorphologyState()

    def update(self, context, gestures, dt: float) -> MorphologyState:
        dt = max(0.0, min(0.1, dt))
        s = self.state

        wave_target = _clamp(
            0.15
            + context.stability * (1.0 - context.zero_crossing_rate) * 0.65
            + gestures.suspension * 0.15
        )
        mass_target = _clamp(
            (1.0 - context.spectral_centroid) * 0.45
            + context.spectral_density * 0.25
            + context.persistence * 0.30
        )
        shard_target = _clamp(
            context.spectral_centroid * 0.30
            + context.zero_crossing_rate * 0.30
            + context.novelty * 0.20
            + gestures.rupture * 0.50
        )
        noise_target = _clamp(
            context.zero_crossing_rate * 0.35
            + (1.0 - context.stability) * 0.30
            + gestures.rupture * 0.30
        )
        roughness_target = _clamp(
            context.zero_crossing_rate * 0.35
            + context.novelty * 0.25
            + gestures.rupture * 0.55
            + s.residue * 0.15
        )
        fluidity_target = _clamp(
            context.stability * 0.55
            + (1.0 - context.zero_crossing_rate) * 0.30
            + wave_target * 0.15
            - shard_target * 0.20
        )
        elasticity_target = _clamp(
            0.25
            + fluidity_target * 0.30
            + gestures.release * 0.25
            + gestures.expansion * 0.20
        )
        symmetry_target = _clamp(
            1.0
            - gestures.rupture * 0.55
            - noise_target * 0.25
            - context.novelty * 0.15
        )
        density_target = _clamp(
            context.spectral_density * 0.50
            + mass_target * 0.30
            + gestures.pressure * 0.20
        )
        fragmentation_target = _clamp(
            gestures.rupture * 0.75
            + gestures.impact * 0.15
            + shard_target * 0.15
        )
        residue_target = max(
            gestures.rupture,
            fragmentation_target * 0.8,
            roughness_target * 0.65,
        )

        s.wave = _approach(s.wave, wave_target, 3.0, 1.2, dt)
        s.mass = _approach(s.mass, mass_target, 2.0, 0.8, dt)
        s.shard = _approach(s.shard, shard_target, 6.0, 1.0, dt)
        s.noise = _approach(s.noise, noise_target, 7.0, 1.5, dt)
        s.roughness = _approach(s.roughness, roughness_target, 7.0, 0.8, dt)
        s.fluidity = _approach(s.fluidity, fluidity_target, 2.5, 1.2, dt)
        s.elasticity = _approach(s.elasticity, elasticity_target, 4.0, 1.0, dt)
        s.symmetry = _approach(s.symmetry, symmetry_target, 2.0, 0.8, dt)
        s.density = _approach(s.density, density_target, 3.0, 1.0, dt)
        s.compression = _approach(s.compression, gestures.pressure, 4.0, 3.0, dt)
        s.expansion = _approach(
            s.expansion,
            _clamp(gestures.expansion * 0.8 + gestures.release * 0.35),
            8.0,
            2.0,
            dt,
        )
        s.fragmentation = _approach(
            s.fragmentation, fragmentation_target, 8.0, 0.7, dt
        )
        s.residue = _approach(s.residue, residue_target, 5.0, 0.22, dt)

        s.brightness = _approach(s.brightness, context.energy, 5.0, 1.5, dt)
        s.saturation = _approach(
            s.saturation,
            _clamp(context.tension * 0.55 + gestures.impact * 0.35 + 0.15),
            5.0,
            1.0,
            dt,
        )
        s.color_stability = _approach(
            s.color_stability, context.stability, 2.0, 1.0, dt
        )
        hue_target = (
            0.58
            + (context.spectral_centroid - 0.5) * 0.38
            + context.activity * 0.08
        ) % 1.0
        hue_delta = (hue_target - s.hue + 0.5) % 1.0 - 0.5
        hue_rate = 0.35 + (1.0 - s.color_stability) * 1.5
        s.hue = (s.hue + hue_delta * (1.0 - math.exp(-hue_rate * dt))) % 1.0

        rotation_speed = (
            0.08
            + context.activity * 0.65
            + s.fluidity * 0.15
            - s.mass * 0.12
        )
        s.rotation += max(0.02, rotation_speed) * dt
        return s
