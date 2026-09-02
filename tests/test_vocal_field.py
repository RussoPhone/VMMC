import unittest
from types import SimpleNamespace

from expression.vocal_field import VocalFieldController


def context(
    activity,
    presence,
    *,
    noise=0.1,
    attack=0.1,
    continuity=0.8,
    stability=0.8,
    tension=0.1,
    prominence=0.3,
    building=0.0,
    climax=0.0,
):
    return SimpleNamespace(
        vocal_activity=activity,
        vocal_presence=presence,
        signature=SimpleNamespace(noisiness=noise, attack=attack),
        signature_continuity=continuity,
        stability=stability,
        tension=tension,
        prominence=prominence,
        regimes=SimpleNamespace(building=building, climax=climax),
    )


class VocalFieldTests(unittest.TestCase):
    def test_soft_continuous_voice_builds_reach_and_continuity_without_pressure(self):
        controller = VocalFieldController()

        for _ in range(20):
            field = controller.update(context(0.35, 0.9), 0.1)

        self.assertGreater(field.radius, field.intensity)
        self.assertGreater(field.continuity, field.pressure)
        self.assertLess(field.roughness, 0.25)

    def test_rough_intense_voice_builds_pressure_and_roughness(self):
        controller = VocalFieldController()

        for _ in range(20):
            field = controller.update(
                context(
                    0.95,
                    0.95,
                    noise=0.9,
                    attack=0.8,
                    tension=0.85,
                    prominence=0.9,
                    building=0.7,
                    climax=0.8,
                ),
                0.1,
            )

        self.assertGreater(field.pressure, 0.6)
        self.assertGreater(field.roughness, 0.5)

    def test_absent_voice_decays_every_channel_without_abrupt_reset(self):
        controller = VocalFieldController()
        for _ in range(20):
            active = controller.update(
                context(0.9, 0.9, noise=0.7, tension=0.8),
                0.1,
            )

        first_quiet = controller.update(
            context(0.0, 0.0, continuity=0.0, stability=0.0),
            0.1,
        )

        self.assertGreater(first_quiet.intensity, 0.0)
        self.assertLess(first_quiet.intensity, active.intensity)
        quiet = first_quiet
        for _ in range(180):
            quiet = controller.update(
                context(0.0, 0.0, continuity=0.0, stability=0.0),
                0.1,
            )
        self.assertTrue(all(value < 0.02 for value in vars(quiet).values()))


if __name__ == "__main__":
    unittest.main()
