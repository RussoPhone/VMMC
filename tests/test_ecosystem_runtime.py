import math
import unittest
from types import SimpleNamespace

from expression.presence_tracker import PresenceTracker
from geometry.ecosystem_geometry import EcosystemGeometryBuilder
from memory.musical_memory import SoundSignature
from state.ecosystem import EcosystemController


class EcosystemRuntimeTests(unittest.TestCase):
    def test_long_transition_remains_finite_and_bounded(self):
        tracker = PresenceTracker()
        ecosystem = EcosystemController()
        geometry = EcosystemGeometryBuilder()

        for index in range(6000):
            timestamp = index / 30.0
            phase = index // 300 % 4
            context = SimpleNamespace(
                signature=SoundSignature(
                    (phase * .23 + math.sin(timestamp) * .04) % 1,
                    .15 + phase * .17,
                    .85 - phase * .17,
                    .2 + (index % 17 == 0) * .6,
                    .35 + phase * .12,
                ),
                prominence=.35 + (index % 31 == 0) * .55,
                cycle_index=0,
            )
            presences = tracker.update(context, timestamp)
            state = ecosystem.update(presences, 1/30, global_cohesion=.5)
            snapshot = geometry.build(state, timestamp)

            for body in state.organisms:
                self.assertTrue(math.isfinite(body.x) and math.isfinite(body.y))
                self.assertLess(math.hypot(body.x, body.y), 4.0)
            for organism in snapshot.organisms:
                self.assertTrue(all(math.isfinite(v) for point in organism.vertices for v in point))

        self.assertLess(len(presences), 20)


if __name__ == "__main__":
    unittest.main()
