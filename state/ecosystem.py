"""Deterministic physical memory for musical organisms and their relations."""

from dataclasses import dataclass
import math

from expression.vocal_field import VocalField
from state.visual_genome import VisualGenome


def _clamp(value):
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class VocalEffect:
    influence: float = 0.0
    fluidity: float = 0.0
    tension: float = 0.0
    roughness: float = 0.0


@dataclass(frozen=True)
class VocalEffectSummary:
    reached_count: int = 0
    mean_influence: float = 0.0
    max_influence: float = 0.0
    mean_fluidity: float = 0.0
    mean_tension: float = 0.0
    mean_roughness: float = 0.0


@dataclass(frozen=True)
class CollisionSummary:
    contact_count: int = 0
    max_repulsion: float = 0.0


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
    vocal_effect: VocalEffect = VocalEffect()


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
    vocal_effect: VocalEffectSummary = VocalEffectSummary()
    collisions: CollisionSummary = CollisionSummary()


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
    vocal_effect: VocalEffect = VocalEffect()


@dataclass
class _Relation:
    fusion: float = 0.0
    assimilation: float = 0.0


class EcosystemController:
    FIELD_RADIUS = 1.6

    def __init__(self):
        self._bodies = {}
        self._relations = {}
        self._core_cohesion = 1.0
        self._cycle_index = None
        self._core_mass = 1.0
        self._time = 0.0

    def update(
        self,
        presences,
        dt,
        global_cohesion=0.5,
        cycle_index=0,
        beat_strength=0.0,
        vocal_field=None,
    ):
        if cycle_index != self._cycle_index:
            self._cycle_index = cycle_index
            self._bodies.clear()
            self._relations.clear()
            self._core_cohesion = 1.0
            self._core_mass = 1.0
            self._time = 0.0
        dt = max(0.0, min(0.1, dt))
        beat_strength = max(0.0, min(1.0, beat_strength))
        vocal_field = vocal_field or VocalField.silent()
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
            body.visibility = (
                presence.visibility
                if presence.active
                else min(body.visibility, presence.visibility)
            )
            body.prominence = presence.prominence
            body.genome = VisualGenome.derive(presence.identifier, presence.signature)
            body.active = presence.active
            body.desired_mass = min(.2, .07 + presence.prominence * .1)

        self._rebalance_mass()
        self._update_vocal_effects(vocal_field, dt)

        relation_states = []
        signature_order = sorted(
            (item for item in visible if item.identifier in self._bodies and item.active),
            key=lambda item: item.signature.brightness,
        )
        for left, right in zip(signature_order, signature_order[1:]):
            relation_states.append(self._update_relation(left, right, dt))

        dissolved = []
        for body in self._bodies.values():
            radius = max(1e-6, math.hypot(body.x, body.y))
            ux, uy = body.x / radius, body.y / radius
            if body.active:
                avoid = max(0.0, .62 - radius) * 2.4
                swirl = .12 + body.prominence * .18
                wander = math.sin(self._time * .73 + body.identifier * 1.91) * .09
                body.vx += (ux * avoid - uy * swirl + math.cos(body.identifier) * wander) * dt
                body.vy += (uy * avoid + ux * swirl + math.sin(body.identifier) * wander) * dt
                effect = body.vocal_effect
                body.vx += (-ux * effect.fluidity * 0.08 - uy * effect.tension * 0.12) * dt
                body.vy += (-uy * effect.fluidity * 0.08 + ux * effect.tension * 0.12) * dt
                if beat_strength > 0.0:
                    speed = math.hypot(body.vx, body.vy)
                    if speed > .01:
                        beat_x, beat_y = body.vx / speed, body.vy / speed
                    else:
                        beat_x, beat_y = ux, uy
                    identity = .35 + body.genome.elasticity * .4 + body.genome.shard * .25
                    impulse = beat_strength * identity * dt
                    body.vx += beat_x * impulse
                    body.vy += beat_y * impulse
            else:
                # An exhausted presence fades where the music left it.  It does
                # not crawl back into the core; only its visual mass dissolves.
                body.visibility *= math.exp(-1.8 * dt)
                body.mass *= math.exp(-1.35 * dt)
            damping = 1.0 - (.18 if body.active else 4.0) * dt
            body.vx *= max(0.0, damping)
            body.vy *= max(0.0, damping)
            body.x += body.vx * dt
            body.y += body.vy * dt
            self._contain(body)
            if not body.active and (body.visibility < .015 or body.mass < .002):
                dissolved.append(body.identifier)

        collisions = self._resolve_collisions(dt)

        for identifier in dissolved:
            self._bodies.pop(identifier)
            self._relations = {
                key: value for key, value in self._relations.items()
                if identifier not in key
            }

        self._rebalance_mass()

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
                body.vocal_effect,
            )
            for body in sorted(self._bodies.values(), key=lambda item: item.identifier)
        )
        return EcosystemState(
            organisms,
            tuple(relation_states),
            self._core_cohesion,
            self._core_mass,
            len(self._bodies),
            self._summarize_vocal_effects(organisms),
            collisions,
        )

    def _update_vocal_effects(self, vocal_field, dt):
        ranked = sorted(
            (body for body in self._bodies.values() if body.active),
            key=lambda body: (
                body.visibility * 0.55 + body.prominence * 0.45,
                -body.identifier,
            ),
            reverse=True,
        )
        denominator = max(1, len(ranked) - 1)
        for index, body in enumerate(ranked):
            position = index / denominator
            reach = _clamp((vocal_field.radius - position + 0.35) / 0.35)
            influence = vocal_field.intensity * reach * body.visibility
            target = VocalEffect(
                influence,
                influence * vocal_field.continuity,
                influence * vocal_field.pressure,
                influence * vocal_field.roughness,
            )
            rate = 8.0 if influence > body.vocal_effect.influence else 2.0
            amount = min(1.0, dt * rate)
            body.vocal_effect = VocalEffect(
                *(
                    getattr(body.vocal_effect, name)
                    + (getattr(target, name) - getattr(body.vocal_effect, name))
                    * amount
                    for name in vars(target)
                )
            )
        for body in self._bodies.values():
            if body.active:
                continue
            amount = min(1.0, dt * 2.0)
            body.vocal_effect = VocalEffect(
                *(value * (1.0 - amount) for value in vars(body.vocal_effect).values())
            )

    @staticmethod
    def _summarize_vocal_effects(organisms):
        effects = [body.vocal_effect for body in organisms]
        if not effects:
            return VocalEffectSummary()
        count = len(effects)
        return VocalEffectSummary(
            sum(effect.influence > 0.01 for effect in effects),
            sum(effect.influence for effect in effects) / count,
            max(effect.influence for effect in effects),
            sum(effect.fluidity for effect in effects) / count,
            sum(effect.tension for effect in effects) / count,
            sum(effect.roughness for effect in effects) / count,
        )

    def _resolve_collisions(self, dt):
        bodies = sorted(self._bodies.values(), key=lambda body: body.identifier)
        contact_count = 0
        max_repulsion = 0.0
        for index, left in enumerate(bodies):
            if left.visibility <= 0.01:
                continue
            for right in bodies[index + 1 :]:
                if right.visibility <= 0.01:
                    continue
                key = (left.identifier, right.identifier)
                relation = self._relations.get(key, _Relation())
                collision_factor = (
                    (1.0 - relation.assimilation) ** 2
                    * (1.0 - relation.fusion * 0.45)
                )
                left_radius = self.visual_radius(left) * 0.58
                right_radius = self.visual_radius(right) * 0.58
                minimum = (left_radius + right_radius) * (
                    0.25 + 0.75 * collision_factor
                )
                dx, dy = right.x - left.x, right.y - left.y
                distance = math.hypot(dx, dy)
                penetration = minimum - distance
                if penetration <= 0.0:
                    continue
                contact_count += 1
                if distance < 1e-9:
                    angle = (left.identifier * 31 + right.identifier * 17) * 0.37
                    ux, uy = math.cos(angle), math.sin(angle)
                else:
                    ux, uy = dx / distance, dy / distance
                normalized = _clamp(penetration / max(minimum, 1e-9))
                repulsion = normalized * collision_factor
                max_repulsion = max(max_repulsion, repulsion)
                displacement = min(0.04, penetration * 0.5) * collision_factor
                left.x -= ux * displacement
                left.y -= uy * displacement
                right.x += ux * displacement
                right.y += uy * displacement
                impulse = repulsion * dt * 0.6
                left.vx -= ux * impulse
                left.vy -= uy * impulse
                right.vx += ux * impulse
                right.vy += uy * impulse
                self._contain(left)
                self._contain(right)
        return CollisionSummary(contact_count, max_repulsion)

    @staticmethod
    def visual_radius(body):
        genome = body.genome
        mass_scale = math.sqrt(max(.01, body.mass) / .1)
        base = (
            (.13 + genome.mass * .15 + body.prominence * .09)
            * (.35 + body.visibility * .65)
            * mass_scale
        )
        return base * 2.1

    def _contain(self, body):
        radius = math.hypot(body.x, body.y)
        limit = max(.15, self.FIELD_RADIUS - self.visual_radius(body))
        if radius <= limit:
            return
        ux, uy = body.x / max(radius, 1e-9), body.y / max(radius, 1e-9)
        body.x, body.y = ux * limit, uy * limit
        outward_speed = body.vx * ux + body.vy * uy
        if outward_speed > 0.0:
            body.vx -= ux * outward_speed * 1.65
            body.vy -= uy * outward_speed * 1.65

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
