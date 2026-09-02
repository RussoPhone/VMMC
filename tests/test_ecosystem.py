import unittest

from expression.presence_tracker import PresenceEvidence, PresenceStage
from memory.musical_memory import SoundSignature
from state.ecosystem import EcosystemController


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

    @staticmethod
    def _presence(identifier, brightness):
        return PresenceEvidence(identifier, SoundSignature(brightness, .2, .8, .3, .5), PresenceStage.CONFIRMED, .9, .7, 2, 3.0, 3.0)

    @staticmethod
    def _distance(left, right):
        return ((left.x-right.x)**2 + (left.y-right.y)**2) ** .5


if __name__ == "__main__":
    unittest.main()
