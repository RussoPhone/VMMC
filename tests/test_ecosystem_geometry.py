import unittest

from geometry.ecosystem_geometry import EcosystemGeometryBuilder
from state.ecosystem import EcosystemState, OrganismState, RelationState
from state.visual_genome import VisualGenome


class EcosystemGeometryTests(unittest.TestCase):
    def test_builds_distinct_organic_bodies_and_fusion_bridge(self):
        genome = VisualGenome(.6,.4,.2,.1,.7,.8,.6,.55,.5,.6)
        state = EcosystemState(
            (OrganismState(1,-.3,0,.9,.8,genome), OrganismState(2,.3,0,.8,.7,genome)),
            (RelationState(1,2,.9,.7,.2),),
            .3,
        )

        snapshot = EcosystemGeometryBuilder(vertex_count=24).build(state, 2.0)

        self.assertEqual(len(snapshot.organisms), 2)
        self.assertEqual(len(snapshot.connections), 1)
        self.assertEqual(len(snapshot.organisms[0].vertices), 24)
        self.assertNotEqual(snapshot.organisms[0].fill_color, snapshot.organisms[0].outline_color)

    def test_assimilation_softens_internal_outlines_without_erasing_lineage(self):
        genome = VisualGenome(.6,.4,.2,.1,.7,.8,.6,.55,.5,.6)
        state = EcosystemState(
            (OrganismState(1,-.1,0,.9,.8,genome), OrganismState(2,.1,0,.8,.7,genome)),
            (RelationState(1,2,.95,.95,.85),),
            .2,
        )

        snapshot = EcosystemGeometryBuilder().build(state, 3.0)

        self.assertEqual({body.identifier for body in snapshot.organisms}, {1, 2})
        self.assertLess(snapshot.organisms[0].outline_alpha, 0.5)


if __name__ == "__main__":
    unittest.main()
