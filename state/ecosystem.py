"""Deterministic physical memory for musical organisms and their relations."""

from dataclasses import dataclass
import math

from state.visual_genome import VisualGenome


@dataclass(frozen=True)
class OrganismState:
    identifier: int
    x: float
    y: float
    visibility: float
    prominence: float
    genome: VisualGenome


@dataclass(frozen=True)
class RelationState:
    left_id: int
    right_id: int
    affinity: float
    fusion: float
    assimilation: float


@dataclass(frozen=True)
class EcosystemState:
    organisms: tuple[OrganismState, ...]
    relations: tuple[RelationState, ...]
    core_cohesion: float
    stored_body_count: int = 0


@dataclass
class _Body:
    identifier: int
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0


@dataclass
class _Relation:
    fusion: float = 0.0
    assimilation: float = 0.0


class EcosystemController:
    def __init__(self):
        self._bodies = {}
        self._relations = {}
        self._core_cohesion = 1.0
        self._cycle_index = None

    def update(self, presences, dt, global_cohesion=0.5, cycle_index=0):
        if cycle_index != self._cycle_index:
            self._cycle_index = cycle_index
            self._bodies.clear()
            self._relations.clear()
            self._core_cohesion = 1.0
        dt = max(0.0, min(0.1, dt))
        visible = sorted(presences, key=lambda item: item.identifier)
        for presence in visible:
            if presence.identifier not in self._bodies:
                angle = presence.identifier * 2.399963229728653
                radius = 0.7 + (presence.identifier % 5) * 0.08
                self._bodies[presence.identifier] = _Body(
                    presence.identifier, math.cos(angle) * radius, math.sin(angle) * radius
                )

        relation_states = []
        signature_order = sorted(visible, key=lambda item: item.signature.brightness)
        for left, right in zip(signature_order, signature_order[1:]):
            relation_states.append(self._update_relation(left, right, dt))

        active_ids = {item.identifier for item in visible}
        for body in self._bodies.values():
            if body.identifier not in active_ids:
                continue
            body.vx *= max(0.0, 1.0 - 2.4 * dt)
            body.vy *= max(0.0, 1.0 - 2.4 * dt)
            body.x += body.vx * dt
            body.y += body.vy * dt

        self._core_cohesion += (global_cohesion - self._core_cohesion) * min(1.0, dt * 0.7)
        organisms = tuple(
            OrganismState(
                item.identifier,
                self._bodies[item.identifier].x,
                self._bodies[item.identifier].y,
                item.visibility,
                item.prominence,
                VisualGenome.derive(item.identifier, item.signature),
            )
            for item in visible
        )
        return EcosystemState(
            organisms,
            tuple(relation_states),
            self._core_cohesion,
            len(self._bodies),
        )

    def _update_relation(self, left, right, dt):
        key = tuple(sorted((left.identifier, right.identifier)))
        relation = self._relations.setdefault(key, _Relation())
        affinity = max(0.0, 1.0 - self._signature_distance(left.signature, right.signature) / 0.35)
        left_body, right_body = self._bodies[left.identifier], self._bodies[right.identifier]
        dx, dy = right_body.x - left_body.x, right_body.y - left_body.y
        distance = math.hypot(dx, dy)
        if distance < 1e-6:
            angle = (left.identifier * 31 + right.identifier * 17) * 0.37
            dx, dy, distance = math.cos(angle) * 1e-6, math.sin(angle) * 1e-6, 1e-6
        attraction = affinity * min(1.0, distance) * 1.8
        separation = (1-affinity) * max(0.0, .65-distance) * 3.0
        force = attraction - separation
        fx, fy = dx / distance * force, dy / distance * force
        left_body.vx += fx * dt
        left_body.vy += fy * dt
        right_body.vx -= fx * dt
        right_body.vy -= fy * dt
        fusion_target = affinity if distance < 0.55 else 0.0
        fusion_rate = 0.8 if fusion_target > relation.fusion else 1.4
        relation.fusion += (fusion_target - relation.fusion) * min(1.0, fusion_rate * dt)
        assimilation_target = max(0.0, (relation.fusion - 0.45) / 0.55)
        assimilation_rate = 0.16 if assimilation_target > relation.assimilation else 0.9
        relation.assimilation += (assimilation_target - relation.assimilation) * min(1.0, assimilation_rate * dt)
        return RelationState(key[0], key[1], affinity, relation.fusion, relation.assimilation)

    @staticmethod
    def _signature_distance(left, right):
        values = [(a-b) ** 2 for a, b in zip(vars(left).values(), vars(right).values())]
        return math.sqrt(sum(values) / len(values))
