"""
renderer/renderer.py (v4 - Eventos expostos para atalhos)

Tolera falta de pygame.mixer, pygame.font, e até display.
Modo texto puro se nada funcionar.
Retorna lista de eventos pygame para o main processar atalhos (ex: 'O' abrir arquivo).
"""

from typing import List, Optional, Sequence, Tuple, Union

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
            print(f"        HUD sera texto puro, sem fonte grafica")
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
        vertices: Sequence[Tuple[float, float]],
        debug_lines: Optional[List[str]] = None,
        fps_limit: int = 60,
    ) -> None:
        if self.headless or self.screen is None:
            # Modo texto: so imprime HUD se mudar (evita spam)
            if debug_lines and debug_lines != self.last_debug_lines:
                self._print_debug_text(debug_lines)
                self.last_debug_lines = debug_lines[:] if debug_lines else []
            self.clock.tick(fps_limit)
            return

        # Modo grafico
        try:
            self.width, self.height = self.screen.get_size()
            self.center, self.radius_px = viewport_for_size(self.width, self.height)
            self.screen.fill((10, 10, 18))

            # Desenha a forma
            points = [
                (self.center[0] + x * self.radius_px, self.center[1] + y * self.radius_px)
                for x, y in vertices
            ]
            if len(points) >= 3:
                pygame.draw.polygon(self.screen, (90, 200, 255), points, width=0)
                pygame.draw.polygon(self.screen, (200, 240, 255), points, width=2)

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
            elif debug_lines and debug_lines != self.last_debug_lines:
                self._print_debug_text(debug_lines)
                self.last_debug_lines = debug_lines[:]

            pygame.display.flip()
        except Exception as e:
            print(f"[AVISO] Erro ao desenhar: {e}")

        self.clock.tick(fps_limit)

    def _print_debug_text(self, debug_lines: List[str]) -> None:
        """Imprime HUD em texto puro no terminal."""
        print("\033[2J\033[H", end="")  # limpa tela (ANSI escape)
        for line in debug_lines:
            print(line)

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
