import math
import unittest

from expression.presence_tracker import PresenceEvidence, PresenceStage
from expression.vocal_field import VocalField
from memory.musical_memory import SoundSignature
from state.ecosystem import EcosystemController, _Relation


class EcosystemTests(unittest.TestCase):
    def test_similar_presences_gravitate_and_assimilate_gradually(self):
        ecosystem = EcosystemController()
        presences = (self._presence(1, 0.30), self._presence(2, 0.32))

        first = ecosystem.update(presences, 0.1, global_cohesion=0.4)
        initial_distance = self._distance(first.organisms[0], first.organisms[1])
        for _ in range(120):
            state = ecosystem.update(presences, 0.1, global_cohesion=0.4)

        relation = state.relations[0]
        self.assertLess(self._distance(state.organisms[0], state.organisms[1]), initial_distance)
        self.assertGreater(relation.fusion, 0.5)
        self.assertGreater(relation.assimilation, 0.0)
        self.assertLess(relation.assimilation, 1.0)
        self.assertNotEqual(state.organisms[0].genome.hue, state.organisms[1].genome.hue)

    def test_divergence_reopens_distinct_nuclei(self):
        ecosystem = EcosystemController()
        similar = (self._presence(1, 0.3), self._presence(2, 0.31))
        for _ in range(120):
            merged = ecosystem.update(similar, 0.1, global_cohesion=0.5)
        merged_distance = self._distance(merged.organisms[0], merged.organisms[1])
        divergent = (self._presence(1, 0.1), self._presence(2, 0.95))
        for _ in range(60):
            separated = ecosystem.update(divergent, 0.1, global_cohesion=0.2)

        self.assertLess(separated.relations[0].fusion, merged.relations[0].fusion)
        self.assertLess(separated.relations[0].assimilation, merged.relations[0].assimilation)
        self.assertGreater(
            self._distance(separated.organisms[0], separated.organisms[1]),
            merged_distance + .1,
        )

    def test_new_musical_cycle_releases_previous_physical_state(self):
        ecosystem = EcosystemController()
        for cycle in range(20):
            state = ecosystem.update(
                (self._presence(cycle + 1, (cycle % 4) * .2),),
                .1,
                cycle_index=cycle,
            )

        self.assertEqual(state.stored_body_count, 1)
        self.assertEqual(state.relations, ())

    def test_core_ejects_new_presence_and_transfers_mass(self):
        ecosystem = EcosystemController()
        presence = self._presence(1, .3)

        born = ecosystem.update((presence,), .1)
        born_radius = math.hypot(born.organisms[0].x, born.organisms[0].y)
        for _ in range(30):
            evolved = ecosystem.update((presence,), .1)

        self.assertLess(born.core_mass, 1.0)
        self.assertGreater(
            math.hypot(evolved.organisms[0].x, evolved.organisms[0].y),
            born_radius + .15,
        )

    def test_inactive_presence_dissolves_without_returning_to_core(self):
        ecosystem = EcosystemController()
        active = self._presence(1, .3)
        for _ in range(40):
            outward = ecosystem.update((active,), .1)
        depleted_core = outward.core_mass
        inactive = PresenceEvidence(**{**vars(active), "active": False})
        inactive_start = ecosystem.update((inactive,), .1)
        start_radius = math.hypot(
            inactive_start.organisms[0].x,
            inactive_start.organisms[0].y,
        )
        observed_radii = [start_radius]
        for _ in range(240):
            dissolved = ecosystem.update((inactive,), .1)
            if dissolved.organisms:
                observed_radii.append(
                    math.hypot(dissolved.organisms[0].x, dissolved.organisms[0].y)
                )

        self.assertEqual(dissolved.organisms, ())
        self.assertGreater(dissolved.core_mass, depleted_core)
        self.assertGreaterEqual(min(observed_radii), start_radius - .02)

    def test_births_never_create_more_mass_than_the_core_owned(self):
        ecosystem = EcosystemController()
        presences = tuple(self._presence(index, (index % 5) * .15) for index in range(1, 21))

        state = ecosystem.update(presences, .1)

        self.assertLessEqual(
            state.core_mass + sum(body.mass for body in state.organisms),
            1.0 + 1e-9,
        )
        self.assertEqual(
            {body.identifier for body in state.organisms},
            {presence.identifier for presence in presences},
        )

    def test_beat_impulses_each_active_form_by_its_visual_identity(self):
        calm = EcosystemController()
        driven = EcosystemController()
        presence = self._presence(4, .7)
        calm.update((presence,), .1, beat_strength=0.0)
        driven.update((presence,), .1, beat_strength=0.0)

        calm_state = calm.update((presence,), .1, beat_strength=0.0)
        driven_state = driven.update((presence,), .1, beat_strength=1.0)

        calm_speed = math.hypot(
            calm_state.organisms[0].velocity_x,
            calm_state.organisms[0].velocity_y,
        )
        driven_speed = math.hypot(
            driven_state.organisms[0].velocity_x,
            driven_state.organisms[0].velocity_y,
        )
        self.assertGreater(driven_speed, calm_speed + .02)

    def test_entire_form_stays_inside_normalized_window(self):
        ecosystem = EcosystemController()
        presence = self._presence(8, .9)

        state = None
        for _ in range(600):
            state = ecosystem.update((presence,), .1, beat_strength=1.0)

        body = state.organisms[0]
        visual_radius = ecosystem.visual_radius(body)
        self.assertLessEqual(math.hypot(body.x, body.y) + visual_radius, 1.6)

    def test_vocal_reach_spreads_continuously_without_creating_a_body(self):
        presences = tuple(
            self._presence(index, index / 10.0) for index in range(1, 5)
        )

        narrow = EcosystemController().update(
            presences,
            0.1,
            vocal_field=VocalField(0.8, 0.15, 0.2, 0.7, 0.3),
        )
        wide = EcosystemController().update(
            presences,
            0.1,
            vocal_field=VocalField(0.8, 0.95, 0.2, 0.7, 0.3),
        )

        self.assertEqual(len(wide.organisms), len(presences))
        self.assertGreater(
            wide.vocal_effect.reached_count,
            narrow.vocal_effect.reached_count,
        )
        self.assertGreater(
            wide.vocal_effect.mean_influence,
            narrow.vocal_effect.mean_influence,
        )

    def test_continuous_voice_changes_motion_and_exposes_transient_effect(self):
        presence = self._presence(4, 0.7)
        plain = EcosystemController()
        voiced = EcosystemController()
        plain.update((presence,), 0.1)
        voiced.update((presence,), 0.1)

        plain_state = plain.update((presence,), 0.1)
        voiced_state = voiced.update(
            (presence,),
            0.1,
            vocal_field=VocalField(0.8, 1.0, 0.1, 0.9, 0.7),
        )

        self.assertGreater(voiced_state.organisms[0].vocal_effect.influence, 0.5)
        self.assertNotEqual(
            (
                voiced_state.organisms[0].velocity_x,
                voiced_state.organisms[0].velocity_y,
            ),
            (
                plain_state.organisms[0].velocity_x,
                plain_state.organisms[0].velocity_y,
            ),
        )
        self.assertEqual(
            voiced_state.organisms[0].genome,
            plain_state.organisms[0].genome,
        )

    def test_unrelated_overlapping_forms_separate_softly(self):
        ecosystem = EcosystemController()
        presences = (self._presence(1, 0.1), self._presence(2, 0.9))
        ecosystem.update(presences, 0.1)
        ecosystem._bodies[1].x = ecosystem._bodies[2].x = 0.5
        ecosystem._bodies[1].y = ecosystem._bodies[2].y = 0.0

        state = ecosystem.update(presences, 0.1)

        self.assertGreater(self._distance(*state.organisms), 0.0)
        self.assertEqual(state.collisions.contact_count, 1)
        self.assertGreater(state.collisions.max_repulsion, 0.0)

    def test_collision_repulsion_fades_through_assimilation(self):
        low = EcosystemController()
        high = EcosystemController()
        presences = (self._presence(1, 0.3), self._presence(2, 0.31))
        for controller in (low, high):
            controller.update(presences, 0.1)
            controller._bodies[1].x = controller._bodies[2].x = 0.5
            controller._bodies[1].y = controller._bodies[2].y = 0.0
        high._relations[(1, 2)] = _Relation(fusion=0.9, assimilation=0.85)

        low_state = low.update(presences, 0.1)
        high_state = high.update(presences, 0.1)

        self.assertLess(
            high_state.collisions.max_repulsion,
            low_state.collisions.max_repulsion,
        )

    @staticmethod
    def _presence(identifier, brightness):
        return PresenceEvidence(identifier, SoundSignature(brightness, .2, .8, .3, .5), PresenceStage.CONFIRMED, .9, .7, 2, 3.0, 3.0, True)

    @staticmethod
    def _distance(left, right):
        return ((left.x-right.x)**2 + (left.y-right.y)**2) ** .5


if __name__ == "__main__":
    unittest.main()
