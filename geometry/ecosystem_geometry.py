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


def _rgb(hue, saturation, luminosity):
    return tuple(
        round(channel * 255)
        for channel in colorsys.hls_to_rgb(hue % 1.0, .14 + luminosity * .55, saturation)
    )


class EcosystemGeometryBuilder:
    def __init__(self, vertex_count=40):
        self.vertex_count = max(12, vertex_count)

    def build(self, ecosystem, time_elapsed):
        relations = {
            identifier: relation
            for relation in ecosystem.relations
            for identifier in (relation.left_id, relation.right_id)
        }
        organisms = tuple(
            self._organism(body, relations.get(body.identifier), time_elapsed)
            for body in ecosystem.organisms
            if body.visibility > .01
        )
        by_id = {body.identifier: body for body in ecosystem.organisms}
        connections = tuple(
            self._connection(by_id[relation.left_id], by_id[relation.right_id], relation)
            for relation in ecosystem.relations
            if relation.fusion > .05
        )
        return EcosystemGeometrySnapshot(organisms, connections)

    def _organism(self, body, relation, time_elapsed):
        genome = body.genome
        scale = (.13 + genome.mass * .15 + body.prominence * .09) * (.35 + body.visibility * .65)
        vertices = []
        for index in range(self.vertex_count):
            angle = math.tau * index / self.vertex_count
            wave = math.sin(angle * 3 + time_elapsed * (.5 + genome.fluidity)) * genome.wave * .09
            shard = max(0, math.sin(angle * 7 + time_elapsed * genome.elasticity)) ** 5 * genome.shard * .12
            rough = math.sin(angle * 13 + body.identifier) * genome.roughness * .035
            asymmetry = math.sin(angle + body.identifier) * (1-genome.symmetry) * .1
            radius = scale * (1 + wave + shard + rough + asymmetry)
            vertices.append((body.x + math.cos(angle) * radius, body.y + math.sin(angle) * radius))
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
