from typing import List, Optional, Sequence, Tuple
import pygame 

class Renderer:
    def __init(self, width: int = 800, height: int = 800, title: str = "Visualizador de Musica com Memoria Contextual"):
        pygame.init()
        pygame.display.set_caption(title)
        self.screen = pygame.display.set_mode((width, height))
        self.width = width
        self.height = height 
        self.center = (width // 2, height // 2)
        self.radius_px = min(width, height) * 0.03
        self.font = pygame.font.SysFont("consolas", 16)
        self.clock = pygame.time.Clock()

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
        return True

    def draw(
        self,
        vertice: Sequence[Tuple[float, float]],
        debug_lines:  Optional[List[str]] = None,
        fps_limit: int = 60,
    ) -> None:
        self.screen.fill((10, 10, 18))

        points = [
            (self.center[0] + x * self.radius_px, self.center[1] + y * self.radius_px)
            for x, y in vertice
        ]
        if len(points) >= 3:
            pygame.draw.polygon(self.screen, (90, 200, 255), points, width=0)
            pygame.draw.polygon(self.screen, (200, 240, 255), points, width=2)

        if debug_lines:
            y_offset = 10
            for line in debug_lines:
                surf = self.font.render(line, True, (255, 255, 255))
                self.screen.blit(surf, (10, y_offset))
                y_offset += 18

        pygame.display.flip()
        self.clock.tick(fps_limit)

    def quit(self) -> None:
        pygame.quit()

