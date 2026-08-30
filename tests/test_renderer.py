import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pygame

import renderer.renderer as renderer_module


class RendererResizeTests(unittest.TestCase):
    def test_exposes_viewport_calculation(self):
        self.assertTrue(hasattr(renderer_module, "viewport_for_size"))

    def test_viewport_tracks_shortest_dimension(self):
        viewport_for_size = renderer_module.viewport_for_size

        self.assertEqual(viewport_for_size(1000, 600), ((500, 300), 180.0))
        self.assertEqual(viewport_for_size(400, 900), ((200, 450), 120.0))

    def test_window_is_created_resizable(self):
        surface = Mock()
        surface.get_size.return_value = (800, 800)
        with (
            patch.object(renderer_module.pygame, "init"),
            patch.object(renderer_module.pygame.time, "Clock", return_value=Mock()),
            patch.object(renderer_module.pygame.display, "set_caption"),
            patch.object(renderer_module.pygame.display, "set_mode", return_value=surface) as set_mode,
            patch.object(
                renderer_module.pygame,
                "font",
                SimpleNamespace(SysFont=Mock(return_value=Mock())),
            ),
        ):
            renderer_module.Renderer()

        set_mode.assert_called_once_with((800, 800), pygame.RESIZABLE)

    def test_draw_refreshes_viewport_from_surface_size(self):
        surface = Mock()
        surface.get_size.return_value = (1000, 600)
        clock = Mock()
        with (
            patch.object(renderer_module.pygame, "init"),
            patch.object(renderer_module.pygame.time, "Clock", return_value=clock),
            patch.object(renderer_module.pygame.display, "set_caption"),
            patch.object(renderer_module.pygame.display, "set_mode", return_value=surface),
            patch.object(renderer_module.pygame.display, "flip"),
            patch.object(
                renderer_module.pygame,
                "font",
                SimpleNamespace(SysFont=Mock(return_value=Mock())),
            ),
            patch.object(renderer_module.pygame.draw, "polygon"),
        ):
            renderer = renderer_module.Renderer()
            renderer.draw([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)])

        self.assertEqual(renderer.center, (500, 300))
        self.assertEqual(renderer.radius_px, 180.0)
        clock.tick.assert_called_once_with(60)


if __name__ == "__main__":
    unittest.main()
