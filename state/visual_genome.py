"""Continuous visual identity cultivated from sound and stable lineage."""

from dataclasses import dataclass
import math


def _clamp(value):
    return max(0.0, min(1.0, value))


def _lineage_variation(identifier, channel):
    value = math.sin(identifier * 12.9898 + channel * 78.233) * 43758.5453
    return (value - math.floor(value)) - 0.5


@dataclass(frozen=True)
class VisualGenome:
    wave: float
    mass: float
    shard: float
    roughness: float
    fluidity: float
    symmetry: float
    elasticity: float
    hue: float
    saturation: float
    luminosity: float

    @classmethod
    def derive(cls, identifier, signature):
        harmonic = signature.harmonicity
        noise = signature.noisiness
        attack = signature.attack
        density = signature.density
        brightness = signature.brightness
        jitter = [_lineage_variation(identifier, index) for index in range(10)]
        return cls(
            wave=_clamp(.18 + harmonic * .62 - noise * .18 + jitter[0] * .08),
            mass=_clamp(.18 + density * .52 + (1-brightness) * .18 + jitter[1] * .12),
            shard=_clamp(.04 + attack * .48 + noise * .24 + jitter[2] * .08),
            roughness=_clamp(.03 + noise * .68 + attack * .18 + jitter[3] * .08),
            fluidity=_clamp(.18 + harmonic * .48 + (1-attack) * .22 + jitter[4] * .08),
            symmetry=_clamp(.35 + harmonic * .48 - noise * .2 + jitter[5] * .1),
            elasticity=_clamp(.2 + attack * .3 + harmonic * .3 + jitter[6] * .1),
            hue=(.52 + brightness * .34 + jitter[7] * .12) % 1.0,
            saturation=_clamp(.28 + attack * .25 + noise * .16 + jitter[8] * .1),
            luminosity=_clamp(.18 + brightness * .42 + density * .18 + jitter[9] * .08),
        )
