"""
renderer/renderer.py (v4 - Eventos expostos para atalhos)

Tolera falta de pygame.mixer, pygame.font, e até display.
Modo texto puro se nada funcionar.
Retorna lista de eventos pygame para o main processar atalhos (ex: 'O' abrir arquivo).
"""

from typing import List, Optional, Sequence, Tuple, Union
from collections import deque
import time

import pygame


def viewport_for_size(width: int, height: int) -> Tuple[Tuple[int, int], float]:
    """Return a centered viewport that preserves the shape proportions."""
    return (width // 2, height // 2), min(width, height) * 0.3


class Renderer:
    def __init__(
        self,
        width: int = 800,
        height: int = 800,
        title: str = "Music Context Visualizer",
    ):
        self.width = width
        self.height = height
        self.center, self.radius_px = viewport_for_size(width, height)
        self.clock = pygame.time.Clock()
        
        self.screen = None
        self.font = None
        self.headless = False
        self.last_debug_lines = []
        self._last_debug_print_time = float("-inf")
        self._debug_print_interval = 0.25
        self._vocal_history = deque(maxlen=240)

        # Tenta inicializar display
        try:
            pygame.display.init()
            pygame.display.set_caption(title)
            self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        except Exception as e:
            print(f"[AVISO] Nao consegui criar janela grafica ({e})")
            print(f"        Usando modo TEXTO no terminal")
            self.headless = True
            return

        # Tenta inicializar font (se display funcionou)
        try:
            self.font = pygame.font.SysFont("consolas", 16)
        except Exception as e:
            print(f"[AVISO] pygame.font nao disponivel ({e})")
            print("        HUD grafico desativado; visualizacao continua normalmente")
            self.font = None

    def handle_events(self) -> Union[List[pygame.event.Event], bool]:
        """
        Processa fila de eventos.
        Retorna:
          - List[pygame.event.Event]: Modo gráfico (main pode filtrar teclas).
          - True: Modo headless (rodando, sem eventos pygame).
          - False: Pedido de quit (modo headless ou erro).
        """
        if self.headless or self.screen is None:
            # Modo texto: não há eventos pygame, apenas roda
            return True

        try:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    return False
                # Não tratamos ESC aqui, deixamos o main decidir
            return events
        except Exception:
            return []  # Retorna lista vazia em erro

    def draw(
        self,
        geometry,
        debug_lines: Optional[List[str]] = None,
        fps_limit: int = 60,
        debug_features=None,
        debug_context=None,
    ) -> None:
        if self.headless or self.screen is None:
            self._maybe_print_debug(debug_lines)
            self.clock.tick(fps_limit)
            return

        # Modo grafico
        try:
            self.width, self.height = self.screen.get_size()
            self.center, self.radius_px = viewport_for_size(self.width, self.height)
            self.screen.fill((10, 10, 18))

            if hasattr(geometry, "organisms"):
                for connection in geometry.connections:
                    points = self._screen_points(connection.vertices)
                    if len(points) >= 3:
                        pygame.draw.polygon(self.screen, connection.color, points, width=0)
                for organism in geometry.organisms:
                    points = self._screen_points(organism.vertices)
                    if len(points) >= 3:
                        pygame.draw.polygon(self.screen, organism.fill_color, points, width=0)
                        alpha = max(0.0, min(1.0, organism.outline_alpha))
                        outline = tuple(
                            round(fill + (edge - fill) * alpha)
                            for fill, edge in zip(
                                organism.fill_color,
                                organism.outline_color,
                            )
                        )
                        pygame.draw.polygon(self.screen, outline, points, width=2)
                for fragment in geometry.fragments:
                    points = self._screen_points(fragment.vertices)
                    if len(points) >= 3:
                        pygame.draw.polygon(self.screen, fragment.color, points, width=0)
                vertices = []
                fragments = []
                fill_color = outline_color = (0, 0, 0)
            elif hasattr(geometry, "body_vertices"):
                vertices = geometry.body_vertices
                fill_color = geometry.fill_color
                outline_color = geometry.outline_color
                fragments = geometry.fragments
            else:
                vertices = geometry
                fill_color = (90, 200, 255)
                outline_color = (200, 240, 255)
                fragments = []

            points = [
                (self.center[0] + x * self.radius_px, self.center[1] + y * self.radius_px)
                for x, y in vertices
            ]
            if len(points) >= 3:
                pygame.draw.polygon(self.screen, fill_color, points, width=0)
                pygame.draw.polygon(self.screen, outline_color, points, width=2)
            for fragment in fragments:
                fragment_points = [
                    (
                        self.center[0] + x * self.radius_px,
                        self.center[1] + y * self.radius_px,
                    )
                    for x, y in fragment.vertices
                ]
                if len(fragment_points) >= 3:
                    pygame.draw.polygon(
                        self.screen,
                        fragment.color,
                        fragment_points,
                        width=0,
                    )

            self._draw_local_frequency_debug(debug_features)
            self._draw_vocal_timeline(debug_context)

            # Desenha HUD se font estiver disponivel
            if debug_lines and self.font:
                try:
                    y_offset = 10
                    for line in debug_lines:
                        surf = self.font.render(line, True, (255, 255, 255))
                        self.screen.blit(surf, (10, y_offset))
                        y_offset += 18
                except Exception as e:
                    print(f"[AVISO] Erro ao desenhar HUD: {e}")

            pygame.display.flip()
        except Exception as e:
            print(f"[AVISO] Erro ao desenhar: {e}")

        self.clock.tick(fps_limit)

    def _draw_local_frequency_debug(self, features):
        if features is None or not hasattr(features, "local_activity"):
            return
        activity = features.local_activity
        novelty = features.local_novelty
        colors = ((238, 112, 76), (74, 205, 174), (170, 124, 255))
        width = min(150, max(75, self.width // 5))
        left = self.width - width - 18
        top = 18
        for index, color in enumerate(colors):
            y = top + index * 18
            pygame.draw.rect(self.screen, (28, 30, 42), (left, y, width, 10))
            pygame.draw.rect(
                self.screen,
                color,
                (left, y, round(width * max(0.0, min(1.0, activity[index]))), 10),
            )
            novelty_width = round(width * max(0.0, min(1.0, novelty[index])))
            pygame.draw.rect(
                self.screen,
                (245, 245, 255),
                (left, y + 12, novelty_width, 2),
            )

    def _draw_vocal_timeline(self, context):
        if context is None or not hasattr(context, "vocal_activity"):
            return
        history = getattr(self, "_vocal_history", None)
        if history is None:
            history = self._vocal_history = deque(maxlen=240)
        history.append(
            (
                max(0.0, min(1.0, context.vocal_activity)),
                max(0.0, min(1.0, context.vocal_presence)),
            )
        )
        width = min(240, max(120, self.width // 3))
        height = 54
        left, top = 18, self.height - height - 18
        pygame.draw.rect(self.screen, (20, 22, 34), (left, top, width, height))
        if len(history) < 2:
            return
        samples = list(history)[-width:]
        step = width / max(1, len(samples) - 1)
        for channel, color in ((0, (80, 225, 210)), (1, (235, 120, 255))):
            points = [
                (
                    round(left + index * step),
                    round(top + height - value[channel] * (height - 4) - 2),
                )
                for index, value in enumerate(samples)
            ]
            pygame.draw.lines(self.screen, color, False, points, 2)

    def _screen_points(self, vertices):
        return [
            (self.center[0] + x * self.radius_px, self.center[1] + y * self.radius_px)
            for x, y in vertices
        ]

    def _print_debug_text(self, debug_lines: List[str]) -> None:
        """Imprime HUD em texto puro no terminal."""
        print("\033[2J\033[H", end="")  # limpa tela (ANSI escape)
        for line in debug_lines:
            print(line)

    def _maybe_print_debug(self, debug_lines: Optional[List[str]]) -> None:
        if not debug_lines or debug_lines == self.last_debug_lines:
            return
        now = time.monotonic()
        last_print = getattr(self, "_last_debug_print_time", float("-inf"))
        interval = getattr(self, "_debug_print_interval", 0.25)
        if now - last_print < interval:
            return
        self._print_debug_text(debug_lines)
        self.last_debug_lines = debug_lines[:]
        self._last_debug_print_time = now

    def quit(self) -> None:
        if self.screen is not None:
            try:
                pygame.display.quit()
            except Exception:
                pass
        try:
            pygame.quit()
        except Exception:
            pass
