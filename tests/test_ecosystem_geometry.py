import math
import unittest
from types import SimpleNamespace

from geometry.ecosystem_geometry import EcosystemGeometryBuilder
from geometry.snapshot import Fragment
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

    def test_global_body_softens_without_disappearing_from_low_cohesion(self):
        core = SimpleNamespace(
            body_vertices=[(-1,0),(0,1),(1,0)],
            fill_color=(10,20,30),
            outline_color=(40,50,60),
            fragments=(Fragment(((.1,0),(.2,.1),(0,.1)), (70,80,90)),),
        )
        coherent = EcosystemState((), (), 1.0)
        dissolved = EcosystemState((), (), 0.0)

        visible = EcosystemGeometryBuilder().build(coherent, 0.0, core)
        hidden = EcosystemGeometryBuilder().build(dissolved, 0.0, core)

        self.assertEqual(visible.organisms[0].identifier, 0)
        self.assertEqual(len(visible.fragments), 1)
        self.assertEqual(hidden.organisms[0].identifier, 0)
        self.assertEqual(hidden.organisms[0].outline_alpha, 0.0)

    def test_core_radius_follows_remaining_mass(self):
        core = SimpleNamespace(body_vertices=[(-1,0),(0,1),(1,0)], fill_color=(10,20,30), outline_color=(40,50,60), fragments=())
        full = EcosystemGeometryBuilder().build(EcosystemState((), (), 1.0, core_mass=1.0), 0, core)
        depleted = EcosystemGeometryBuilder().build(EcosystemState((), (), 1.0, core_mass=.25), 0, core)

        self.assertGreater(abs(full.organisms[0].vertices[0][0]), abs(depleted.organisms[0].vertices[0][0]) * 1.8)

    def test_mutable_sound_has_larger_living_deformation(self):
        clean = VisualGenome(.8,.4,.05,.03,.8,.9,.5,.55,.5,.6)
        mutable = VisualGenome(.2,.4,.8,.9,.3,.2,.8,.55,.5,.6)
        clean_state = EcosystemState((OrganismState(1,.6,0,.9,.8,clean),),(),.5)
        mutable_state = EcosystemState((OrganismState(1,.6,0,.9,.8,mutable),),(),.5)
        builder = EcosystemGeometryBuilder(vertex_count=40)

        clean_a, clean_b = builder.build(clean_state, 0).organisms[0], builder.build(clean_state, 1).organisms[0]
        mutable_a, mutable_b = builder.build(mutable_state, 0).organisms[0], builder.build(mutable_state, 1).organisms[0]
        clean_motion = sum(math.dist(a,b) for a,b in zip(clean_a.vertices, clean_b.vertices))
        mutable_motion = sum(math.dist(a,b) for a,b in zip(mutable_a.vertices, mutable_b.vertices))

        self.assertGreater(mutable_motion, clean_motion * 1.5)


if __name__ == "__main__":
    unittest.main()
