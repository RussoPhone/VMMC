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
    mass: float = 0.1
    velocity_x: float = 0.0
    velocity_y: float = 0.0


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
    core_mass: float = 1.0
    stored_body_count: int = 0


@dataclass
class _Body:
    identifier: int
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    visibility: float = 0.0
    prominence: float = 0.0
    genome: VisualGenome | None = None
    mass: float = 0.1
    active: bool = True
    desired_mass: float = 0.1


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
        self._core_mass = 1.0
        self._time = 0.0

    def update(self, presences, dt, global_cohesion=0.5, cycle_index=0):
        if cycle_index != self._cycle_index:
            self._cycle_index = cycle_index
            self._bodies.clear()
            self._relations.clear()
            self._core_cohesion = 1.0
            self._core_mass = 1.0
            self._time = 0.0
        dt = max(0.0, min(0.1, dt))
        self._time += dt
        visible = sorted(presences, key=lambda item: item.identifier)
        for presence in visible:
            if presence.identifier not in self._bodies:
                if not presence.active:
                    continue
                angle = presence.identifier * 2.399963229728653
                desired_mass = min(.2, .07 + presence.prominence * .1)
                mass = desired_mass
                radius = .28 + math.sqrt(max(.05, self._core_mass)) * .18
                self._bodies[presence.identifier] = _Body(
                    presence.identifier,
                    math.cos(angle) * radius,
                    math.sin(angle) * radius,
                    math.cos(angle) * (.28 + presence.prominence * .18),
                    math.sin(angle) * (.28 + presence.prominence * .18),
                    presence.visibility,
                    presence.prominence,
                    VisualGenome.derive(presence.identifier, presence.signature),
                    mass,
                    presence.active,
                    desired_mass,
                )
            body = self._bodies.get(presence.identifier)
            if body is None:
                continue
            body.visibility = presence.visibility
            body.prominence = presence.prominence
            body.genome = VisualGenome.derive(presence.identifier, presence.signature)
            body.active = presence.active
            body.desired_mass = min(.2, .07 + presence.prominence * .1)

        self._rebalance_mass()

        relation_states = []
        signature_order = sorted(
            (item for item in visible if item.identifier in self._bodies and item.active),
            key=lambda item: item.signature.brightness,
        )
        for left, right in zip(signature_order, signature_order[1:]):
            relation_states.append(self._update_relation(left, right, dt))

        returned = []
        for body in self._bodies.values():
            radius = max(1e-6, math.hypot(body.x, body.y))
            ux, uy = body.x / radius, body.y / radius
            if body.active:
                avoid = max(0.0, .62 - radius) * 2.4
                swirl = .12 + body.prominence * .18
                wander = math.sin(self._time * .73 + body.identifier * 1.91) * .09
                body.vx += (ux * avoid - uy * swirl + math.cos(body.identifier) * wander) * dt
                body.vy += (uy * avoid + ux * swirl + math.sin(body.identifier) * wander) * dt
                if radius > 1.25:
                    body.vx -= ux * (radius - 1.25) * 1.8 * dt
                    body.vy -= uy * (radius - 1.25) * 1.8 * dt
            else:
                body.vx += (-body.x * 1.35 - body.vx * .9) * dt
                body.vy += (-body.y * 1.35 - body.vy * .9) * dt
            damping = 1.0 - (.18 if body.active else .55) * dt
            body.vx *= max(0.0, damping)
            body.vy *= max(0.0, damping)
            body.x += body.vx * dt
            body.y += body.vy * dt
            if not body.active and math.hypot(body.x, body.y) < .2:
                returned.append(body.identifier)

        for identifier in returned:
            body = self._bodies.pop(identifier)
            self._core_mass = min(1.0, self._core_mass + body.mass)
            self._relations = {
                key: value for key, value in self._relations.items()
                if identifier not in key
            }

        self._core_cohesion += (global_cohesion - self._core_cohesion) * min(1.0, dt * 0.7)
        organisms = tuple(
            OrganismState(
                body.identifier,
                body.x,
                body.y,
                body.visibility,
                body.prominence,
                body.genome,
                body.mass,
                body.vx,
                body.vy,
            )
            for body in sorted(self._bodies.values(), key=lambda item: item.identifier)
        )
        return EcosystemState(
            organisms,
            tuple(relation_states),
            self._core_cohesion,
            self._core_mass,
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
        attraction = affinity * min(1.0, distance) * .9
        separation = (1-affinity) * max(0.0, .48-distance) * 3.0
        force = attraction - separation
        fx, fy = dx / distance * force, dy / distance * force
        left_body.vx += fx * dt
        left_body.vy += fy * dt
        right_body.vx -= fx * dt
        right_body.vy -= fy * dt
        fusion_target = affinity if distance < 0.68 else 0.0
        fusion_rate = 0.8 if fusion_target > relation.fusion else 1.4
        relation.fusion += (fusion_target - relation.fusion) * min(1.0, fusion_rate * dt)
        assimilation_target = max(0.0, (relation.fusion - 0.45) / 0.55)
        assimilation_rate = 0.16 if assimilation_target > relation.assimilation else 0.9
        relation.assimilation += (assimilation_target - relation.assimilation) * min(1.0, assimilation_rate * dt)
        return RelationState(key[0], key[1], affinity, relation.fusion, relation.assimilation)

    def _rebalance_mass(self):
        inactive_mass = sum(body.mass for body in self._bodies.values() if not body.active)
        active = [body for body in self._bodies.values() if body.active]
        desired_total = sum(body.desired_mass for body in active)
        available = max(0.0, .92 - inactive_mass)
        scale = min(1.0, available / desired_total) if desired_total else 0.0
        for body in active:
            body.mass = body.desired_mass * scale
        self._core_mass = max(
            .08,
            1.0 - inactive_mass - sum(body.mass for body in active),
        )

    @staticmethod
    def _signature_distance(left, right):
        values = [(a-b) ** 2 for a, b in zip(vars(left).values(), vars(right).values())]
        return math.sqrt(sum(values) / len(values))
