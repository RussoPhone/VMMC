import unittest

from memory.musical_memory import SoundSignature
from state.visual_genome import VisualGenome


class VisualGenomeTests(unittest.TestCase):
    def test_same_lineage_and_signature_are_deterministic(self):
        signature = SoundSignature(.4, .2, .8, .3, .6)

        self.assertEqual(
            VisualGenome.derive(7, signature),
            VisualGenome.derive(7, signature),
        )

    def test_different_lineages_are_related_but_not_identical(self):
        signature = SoundSignature(.4, .2, .8, .3, .6)

        left = VisualGenome.derive(7, signature)
        right = VisualGenome.derive(8, signature)

        self.assertNotEqual(left.hue, right.hue)
        self.assertLess(abs(left.mass - right.mass), .25)

    def test_signature_cultivates_continuous_visual_properties(self):
        smooth = VisualGenome.derive(1, SoundSignature(.3, .05, .95, .1, .5))
        rough = VisualGenome.derive(1, SoundSignature(.8, .9, .1, .9, .5))

        self.assertGreater(smooth.wave, rough.wave)
        self.assertGreater(rough.roughness, smooth.roughness)
        for value in vars(rough).values():
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)


if __name__ == "__main__":
    unittest.main()
