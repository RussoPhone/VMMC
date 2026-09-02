import math
import unittest

from geometry.deformation import GeometryBuilder
from geometry.shape import create_circle_shape
from state.morphology import MorphologyState


class ExpressiveGeometryTests(unittest.TestCase):
    def test_neutral_morphology_remains_close_to_circle(self):
        snapshot = GeometryBuilder().build(
            create_circle_shape(72), MorphologyState(), 0.0, 1.0 / 60.0
        )
        radii = [math.hypot(x, y) for x, y in snapshot.body_vertices]

        self.assertLess(max(radii) - min(radii), 0.2)
        self.assertEqual(snapshot.fragments, [])

    def test_same_inputs_are_deterministic(self):
        shape = create_circle_shape(72)
        morphology = MorphologyState(
            wave=0.8,
            shard=0.4,
            noise=0.3,
            hue=0.2,
            saturation=0.7,
            brightness=0.6,
        )

        first = GeometryBuilder().build(shape, morphology, 2.5, 1.0 / 60.0)
        second = GeometryBuilder().build(shape, morphology, 2.5, 1.0 / 60.0)

        self.assertEqual(first, second)

    def test_small_time_step_moves_body_continuously(self):
        shape = create_circle_shape(72)
        morphology = MorphologyState(wave=0.8, shard=0.5, roughness=0.6)
        builder = GeometryBuilder()
        before = builder.build(shape, morphology, 1.0, 1.0 / 60.0)
        after = builder.build(shape, morphology, 1.01, 0.01)
        displacement = sum(
            math.dist(a, b)
            for a, b in zip(before.body_vertices, after.body_vertices)
        ) / len(before.body_vertices)

        self.assertLess(displacement, 0.05)

    def test_fragmentation_is_bounded_and_returns_under_calm(self):
        shape = create_circle_shape(72)
        builder = GeometryBuilder(max_fragments=6)
        rupture = MorphologyState(
            shard=0.9,
            roughness=0.9,
            fragmentation=1.0,
            expansion=0.8,
            elasticity=0.7,
        )
        burst = builder.build(shape, rupture, 1.0, 1.0 / 30.0)

        self.assertGreater(len(burst.fragments), 0)
        self.assertLessEqual(len(burst.fragments), 6)

        calm = MorphologyState(fragmentation=0.0, elasticity=0.8, symmetry=1.0)
        snapshot = burst
        for index in range(180):
            snapshot = builder.build(
                shape,
                calm,
                1.0 + (index + 1) / 30.0,
                1.0 / 30.0,
            )

        self.assertLess(len(snapshot.fragments), len(burst.fragments))

    def test_crescendo_lift_raises_the_whole_core(self):
        shape = create_circle_shape(72)
        resting = GeometryBuilder().build(shape, MorphologyState(lift=0.0), 1.0, 1/60)
        raised = GeometryBuilder().build(shape, MorphologyState(lift=0.8), 1.0, 1/60)

        resting_y = sum(y for _, y in resting.body_vertices) / len(resting.body_vertices)
        raised_y = sum(y for _, y in raised.body_vertices) / len(raised.body_vertices)
        self.assertLess(raised_y, resting_y - .15)


if __name__ == "__main__":
    unittest.main()
