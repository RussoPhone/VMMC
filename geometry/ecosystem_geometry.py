"""Organic compound geometry for a persistent musical ecosystem."""

import colorsys
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class OrganismGeometry:
    identifier: int
    vertices: tuple
    fill_color: tuple
    outline_color: tuple
    outline_alpha: float


@dataclass(frozen=True)
class ConnectionGeometry:
    vertices: tuple
    color: tuple


@dataclass(frozen=True)
class EcosystemGeometrySnapshot:
    organisms: tuple
    connections: tuple
    fragments: tuple = ()


def _rgb(hue, saturation, luminosity):
    return tuple(
        round(channel * 255)
        for channel in colorsys.hls_to_rgb(hue % 1.0, .14 + luminosity * .55, saturation)
    )


def _clamp(value):
    return max(0.0, min(1.0, value))


class EcosystemGeometryBuilder:
    def __init__(self, vertex_count=40):
        self.vertex_count = max(12, vertex_count)

    def build(self, ecosystem, time_elapsed, core_geometry=None):
        fragments = ()
        relations = {}
        for relation in ecosystem.relations:
            for identifier in (relation.left_id, relation.right_id):
                current = relations.get(identifier)
                if current is None or relation.assimilation > current.assimilation:
                    relations[identifier] = relation
        organisms = tuple(
            self._organism(body, relations.get(body.identifier), time_elapsed)
            for body in ecosystem.organisms
            if body.visibility > .01
        )
        if core_geometry is not None and ecosystem.core_mass > .02:
            cohesion = ecosystem.core_cohesion
            core_scale = math.sqrt(ecosystem.core_mass) * (.72 + cohesion * .28)
            core = OrganismGeometry(
                0,
                tuple((x * core_scale, y * core_scale) for x, y in core_geometry.body_vertices),
                core_geometry.fill_color,
                core_geometry.outline_color,
                cohesion,
            )
            organisms = (core,) + organisms
            fragments = tuple(
                type(fragment)(
                    tuple((x * core_scale, y * core_scale) for x, y in fragment.vertices),
                    fragment.color,
                )
                for fragment in core_geometry.fragments
            )
        by_id = {body.identifier: body for body in ecosystem.organisms}
        connections = tuple(
            self._connection(by_id[relation.left_id], by_id[relation.right_id], relation)
            for relation in ecosystem.relations
            if relation.fusion > .05
        )
        return EcosystemGeometrySnapshot(organisms, connections, fragments)

    def _organism(self, body, relation, time_elapsed):
        genome = body.genome
        effect = body.vocal_effect
        fluidity = _clamp(genome.fluidity + effect.fluidity * 0.35)
        roughness = _clamp(genome.roughness + effect.roughness * 0.45)
        tension = effect.tension
        mass_scale = math.sqrt(max(.01, body.mass) / .1)
        scale = (.13 + genome.mass * .15 + body.prominence * .09) * (.35 + body.visibility * .65) * mass_scale
        vertices = []
        orientation = math.atan2(body.velocity_y, body.velocity_x)
        speed = min(1.0, math.hypot(body.velocity_x, body.velocity_y))
        for index in range(self.vertex_count):
            angle = math.tau * index / self.vertex_count
            wave = math.sin(angle * 3 + time_elapsed * (.35 + fluidity * .45)) * genome.wave * .045
            shard = max(0, math.sin(angle * 7 + time_elapsed * genome.elasticity)) ** 5 * genome.shard * .12
            rough = math.sin(angle * 13 + body.identifier) * roughness * .035
            rough += (
                math.sin(angle * 17 + time_elapsed * 0.9 + body.identifier)
                * effect.roughness
                * 0.06
            )
            vocal_tension = math.sin(angle * 2 - time_elapsed * 1.3) * tension * 0.08
            asymmetry = math.sin(angle + body.identifier) * (1-genome.symmetry) * .1
            mutation = roughness * .55 + genome.shard * .45
            living_lobes = math.sin(
                angle * (4 + round(genome.shard * 5))
                + time_elapsed * (1.4 + genome.elasticity * 2.2)
                + math.sin(time_elapsed * .61 + body.identifier) * 1.2
            ) * mutation * .23
            extension_direction = orientation + math.sin(
                time_elapsed * .47 + body.identifier
            ) * .8
            extension = max(0.0, math.cos(angle - extension_direction)) ** 8
            extension *= mutation * (.35 + genome.elasticity * .45)
            concavity = max(0.0, math.sin(angle * 2 - time_elapsed * .8)) ** 6
            concavity *= genome.roughness * .18
            radius = scale * (
                1 + wave + shard + rough + asymmetry + living_lobes
                + extension - concavity + vocal_tension
            )
            stretch = 1 + speed * .55 + genome.shard * .22 + tension * 0.16
            local_x = math.cos(angle) * radius * stretch
            local_y = math.sin(angle) * radius / math.sqrt(stretch)
            cos_o, sin_o = math.cos(orientation), math.sin(orientation)
            vertices.append(
                (
                    body.x + local_x * cos_o - local_y * sin_o,
                    body.y + local_x * sin_o + local_y * cos_o,
                )
            )
        assimilation = relation.assimilation if relation else 0.0
        return OrganismGeometry(
            body.identifier,
            tuple(vertices),
            _rgb(genome.hue, genome.saturation, genome.luminosity * body.visibility),
            _rgb(genome.hue + .025, min(1, genome.saturation * .65 + .2), min(1, genome.luminosity + .28)),
            max(.12, 1-assimilation),
        )

    @staticmethod
    def _connection(left, right, relation):
        dx, dy = right.x-left.x, right.y-left.y
        length = max(1e-6, math.hypot(dx, dy))
        width = .025 + relation.fusion * .07
        nx, ny = -dy/length*width, dx/length*width
        vertices = ((left.x+nx,left.y+ny),(right.x+nx,right.y+ny),(right.x-nx,right.y-ny),(left.x-nx,left.y-ny))
        hue = (left.genome.hue + right.genome.hue) * .5
        color = _rgb(hue, .35 + relation.affinity*.3, .18 + relation.fusion*.3)
        return ConnectionGeometry(vertices, color)
