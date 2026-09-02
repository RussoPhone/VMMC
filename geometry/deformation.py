import colorsys
import math
from dataclasses import dataclass

from geometry.snapshot import Fragment, GeometrySnapshot


def _rgb(hue, saturation, brightness):
    lightness = 0.16 + max(0.0, min(1.0, brightness)) * 0.62
    red, green, blue = colorsys.hls_to_rgb(
        hue % 1.0,
        lightness,
        max(0.0, min(1.0, saturation)),
    )
    return tuple(int(round(channel * 255)) for channel in (red, green, blue))


@dataclass
class _FragmentState:
    sector: int
    age: float = 0.0
    offset: float = 0.0


class GeometryBuilder:
    def __init__(self, max_fragments: int = 6):
        self.max_fragments = max(0, max_fragments)
        self._fragments = []
        self._render_rotation = 0.0
        self._stretch = 0.0
        self._display_color = None

    def build(self, shape, morphology, time_elapsed: float, dt: float):
        dt = max(0.0, min(0.1, dt))
        self._advance_motion(morphology, time_elapsed, dt)
        hue, saturation, brightness = self._smooth_color(morphology, dt)
        body = self._body_vertices(shape, morphology, time_elapsed)
        pulse = 0.5 + 0.5 * math.sin(
            time_elapsed * (1.15 + morphology.elasticity * 0.9)
        )
        brightness = min(1.0, brightness + pulse * morphology.brightness * 0.08)
        fill = _rgb(hue, saturation, brightness)
        outline = _rgb(
            hue + 0.025,
            min(1.0, saturation * 0.65 + 0.2),
            min(1.0, brightness + 0.28),
        )
        self._update_fragments(shape, morphology, dt)
        fragments = self._fragment_geometry(body, morphology, outline)
        return GeometrySnapshot(body, fragments, fill, outline)

    def _advance_motion(self, morphology, time_elapsed, dt):
        rotation_speed = 0.08 + morphology.fluidity * 0.32 + morphology.wave * 0.12
        self._render_rotation += rotation_speed * dt
        oscillation = math.sin(
            time_elapsed * (1.4 + morphology.fluidity * 1.4)
        )
        strength = (
            0.018
            + morphology.expansion * 0.16
            + morphology.compression * 0.13
            + morphology.elasticity * 0.025
        )
        target = oscillation * strength
        alpha = 1.0 - math.exp(-10.0 * dt)
        self._stretch += (target - self._stretch) * alpha

    def _smooth_color(self, morphology, dt):
        target = (morphology.hue, morphology.saturation, morphology.brightness)
        if self._display_color is None:
            self._display_color = target
            return target
        hue, saturation, brightness = self._display_color
        alpha = 1.0 - math.exp(-8.0 * dt)
        hue_delta = (target[0] - hue + 0.5) % 1.0 - 0.5
        hue = (hue + hue_delta * alpha) % 1.0
        saturation += (target[1] - saturation) * alpha
        brightness += (target[2] - brightness) * alpha
        self._display_color = (hue, saturation, brightness)
        return self._display_color

    def _body_vertices(self, shape, morphology, time_elapsed):
        scale = (
            1.0
            + morphology.mass * 0.08
            + morphology.expansion * 0.34
            - morphology.compression * 0.18
        )
        breath = math.sin(
            time_elapsed * (0.9 + morphology.fluidity * 0.8)
        ) * (0.008 + morphology.wave * 0.018 + morphology.brightness * 0.018)
        scale *= 1.0 + breath
        vertices = []
        for angle in shape.base_angles:
            wave = (
                math.sin(angle * 3.0 + time_elapsed * (0.45 + morphology.fluidity))
                * morphology.wave
                * 0.08
            )
            shard_wave = max(
                0.0,
                math.sin(angle * 7.0 + time_elapsed * (0.7 + morphology.elasticity)),
            ) ** 5
            shard = shard_wave * morphology.shard * 0.13
            detail = (
                math.sin(angle * 13.0 + time_elapsed * 1.71)
                + math.sin(angle * 17.0 - time_elapsed * 2.13) * 0.55
            ) * (morphology.noise * 0.018 + morphology.roughness * 0.028)
            asymmetry = (
                math.sin(angle + 0.73 + time_elapsed * 0.17)
                * (1.0 - morphology.symmetry)
                * 0.12
            )
            radius = max(0.2, scale * (1.0 + wave + shard + detail + asymmetry))
            squeeze = 1.0 - morphology.compression * (
                0.06 + 0.08 * (0.5 + 0.5 * math.cos(angle * 2.0))
            )
            rotated = angle + self._render_rotation
            vertices.append(
                (
                    math.cos(rotated) * radius * squeeze * (1.0 + self._stretch),
                    math.sin(rotated)
                    * radius
                    / max(0.75, squeeze)
                    * (1.0 - self._stretch * 0.72),
                )
            )
        return vertices

    def _update_fragments(self, shape, morphology, dt):
        desired = min(
            self.max_fragments,
            int(round(morphology.fragmentation * self.max_fragments)),
        )
        used_sectors = {fragment.sector for fragment in self._fragments}
        for index in range(self.max_fragments):
            if len(self._fragments) >= desired:
                break
            sector = int(index * shape.vertex_count / max(1, self.max_fragments))
            if sector not in used_sectors:
                self._fragments.append(_FragmentState(sector=sector))
                used_sectors.add(sector)

        life = 1.0 + morphology.elasticity * 1.8 + morphology.residue * 1.2
        survivors = []
        for fragment in self._fragments:
            fragment.age += dt
            drive = morphology.expansion * 0.9 + morphology.fragmentation * 0.5
            return_force = (1.0 - morphology.fragmentation) * morphology.elasticity
            fragment.offset = max(
                0.0,
                fragment.offset + drive * dt - return_force * fragment.offset * dt,
            )
            if morphology.fragmentation > 0.05 or fragment.age < life:
                survivors.append(fragment)
        self._fragments = survivors[: self.max_fragments]

    def _fragment_geometry(self, body, morphology, color):
        fragments = []
        count = len(body)
        for fragment in self._fragments:
            index = fragment.sector % count
            previous = body[(index - 1) % count]
            center = body[index]
            following = body[(index + 1) % count]
            length = max(1e-9, math.hypot(*center))
            direction = (center[0] / length, center[1] / length)
            distance = fragment.offset * (0.22 + morphology.expansion * 0.25)
            shift = (direction[0] * distance, direction[1] * distance)
            points = tuple(
                (point[0] + shift[0], point[1] + shift[1])
                for point in (previous, center, following)
            )
            fragments.append(Fragment(points, color))
        return fragments
