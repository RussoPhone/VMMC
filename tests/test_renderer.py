import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pygame

import renderer.renderer as renderer_module


class RendererResizeTests(unittest.TestCase):
    def test_draw_uses_snapshot_body_fragment_and_colors(self):
        renderer = object.__new__(renderer_module.Renderer)
        renderer.width = 800
        renderer.height = 800
        renderer.screen = Mock()
        renderer.screen.get_size.return_value = (800, 800)
        renderer.font = None
        renderer.headless = False
        renderer.last_debug_lines = []
        renderer.clock = Mock()
        snapshot = SimpleNamespace(
            body_vertices=[(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)],
            fragments=[
                SimpleNamespace(
                    vertices=((0.2, 0.2), (0.3, 0.2), (0.2, 0.3)),
                    color=(220, 120, 80),
                )
            ],
            fill_color=(20, 40, 60),
            outline_color=(100, 140, 180),
        )

        with (
            patch.object(renderer_module.pygame.draw, "polygon") as polygon,
            patch.object(renderer_module.pygame.display, "flip"),
        ):
            renderer.draw(snapshot)

        colors = [call.args[1] for call in polygon.call_args_list]
        self.assertEqual(colors, [(20, 40, 60), (100, 140, 180), (220, 120, 80)])

    def test_initializes_only_display_instead_of_all_pygame_modules(self):
        surface = Mock()
        surface.get_size.return_value = (800, 800)
        with (
            patch.object(renderer_module.pygame, "init") as init_all,
            patch.object(renderer_module.pygame.display, "init") as init_display,
            patch.object(renderer_module.pygame.time, "Clock", return_value=Mock()),
            patch.object(renderer_module.pygame.display, "set_caption"),
            patch.object(renderer_module.pygame.display, "set_mode", return_value=surface),
            patch.object(
                renderer_module.pygame,
                "font",
                SimpleNamespace(SysFont=Mock(side_effect=RuntimeError("font unavailable"))),
            ),
        ):
            renderer_module.Renderer()

        init_display.assert_called_once_with()
        init_all.assert_not_called()

    def test_draw_prints_debug_when_window_has_no_font(self):
        renderer = object.__new__(renderer_module.Renderer)
        renderer.width = 800
        renderer.height = 800
        renderer.screen = Mock()
        renderer.screen.get_size.return_value = (800, 800)
        renderer.font = None
        renderer.headless = False
        renderer.last_debug_lines = []
        renderer.clock = Mock()
        renderer._print_debug_text = Mock()

        with (
            patch.object(renderer_module.pygame.draw, "polygon"),
            patch.object(renderer_module.pygame.display, "flip"),
        ):
            renderer.draw(
                [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)],
                ["energy=0.50"],
            )

        renderer._print_debug_text.assert_called_once_with(["energy=0.50"])

    def test_terminal_debug_is_throttled_when_values_change_each_frame(self):
        renderer = object.__new__(renderer_module.Renderer)
        renderer.width = 800
        renderer.height = 800
        renderer.screen = Mock()
        renderer.screen.get_size.return_value = (800, 800)
        renderer.font = None
        renderer.headless = False
        renderer.last_debug_lines = []
        renderer.clock = Mock()
        renderer._print_debug_text = Mock()

        with (
            patch.object(renderer_module.pygame.draw, "polygon"),
            patch.object(renderer_module.pygame.display, "flip"),
        ):
            renderer.draw([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)], ["energy=0.50"])
            renderer.draw([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)], ["energy=0.51"])

        renderer._print_debug_text.assert_called_once()

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
            patch.object(renderer_module.pygame.display, "init"),
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
            patch.object(renderer_module.pygame.display, "init"),
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
