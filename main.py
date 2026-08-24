import sys
import time
import os

from audio.input import AudioInput
from audio.analyzer import AudioAnalyzer 
from memory.musical_memory import MusicalMemory 
from state.visual_state import VisualStateController
from geometry.shape import create_circle_shape
from geometry.deformation import deform_shape  
from renderer.renderer import Renderer 

def select_audio_file() -> str:
    """Tenta abrir uma janela de seleção de arquivo se possível, caso contrário pede manualmente."""
    try:
        import pygame
        pygame.init()
        
        # Cria uma janela pequena para seleção de arquivo
        screen = pygame.display.set_mode((400, 200))
        pygame.display.set_caption("Selecionar Música")
        font = pygame.font.SysFont(None, 36)
        
        running = True
        selected_file = None
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_RETURN and selected_file:
                        running = False
            
            screen.fill((30, 30, 50))
            
            # Mostra instruções
            text = font.render("Pressione Enter para selecionar um arquivo de música", True, (255, 255, 255))
            screen.blit(text, (20, 50))
            
            text = font.render("ou ESC para sair", True, (200, 200, 200))
            screen.blit(text, (20, 100))
            
            pygame.display.flip()
            
            # Se já temos um arquivo selecionado, podemos sair
            if selected_file:
                break
                
        pygame.quit()
        
        # Se não foi selecionado arquivo, pedimos manualmente
        if not selected_file:
            print("Selecione um arquivo de música:")
            file_path = input().strip()
            return file_path
            
    except ImportError:
        # Se Pygame não estiver disponível, pedimos manualmente
        print("Selecione um arquivo de música:")
        file_path = input().strip()
        return file_path

def main(audio_path: str) -> None:
    audio_input = AudioInput(audio_path)
    analyzer = AudioAnalyzer()
    memory = MusicalMemory()
    visual_controller = VisualStateController() 
    shape = create_circle_shape(vertex_count=72)
    renderer = Renderer()

    audio_input.play()
    start_time = time.time()
    last_time = start_time 

    latest_features = None
    latest_context = None 

    running = True 
    while running:
        running = renderer.handle_events()

        now = time.time() 
        dt = now - last_time 
        last_time = now 

        frame = audio_input.get_next_frame()
        if frame is not None:
            latest_features = analyzer.analyze(frame)
            latest_context = memory.update(latest_features)

        if latest_context is not None: 
            visual_state = visual_controller.update(latest_context, dt)
        else:
            visual_state = visual_controller.state

        time_elapsed = now - start_time
        vertices = deform_shape(shape, visual_state, time_elapsed)

        debug_lines = _build_debug_lines(latest_features, latest_context, visual_state)
        renderer.draw(vertices, debug_lines)

        if audio_input.is_finished():
            running = False

    renderer.quit()

def _build_debug_lines(features, context, visual_state) -> list:
    lines = ["VISUALIZADOR DE MUSICA COM MEMORIA CONTEXTUAL"]
    if features:
        lines.append(
            f"amp={features.amplitude:.2f} bass={features.bass:.2f} "
            f"mid={features.mid:.2f} treble={features.treble:.2f} "
            f"flux={features.spectral_flux:.2f} beat={'*' if features.beat else ' '}"
        )
    if context:
        lines.append(
            f"energy={context.energy:.2f} avg={context.energy_average:.2f} "
            f"trend={context.energy_trend:+.2f} activity={context.activity:.2f} "
            f"tension={context.tension:.2f}"
        )
    lines.append(
        f"scale={visual_state.scale:.2f} deform={visual_state.deformation:.2f} "
    f"agitation={visual_state.agitation:.2f} smooth={visual_state.smoothness:.2f}"
    )
    return lines

if __name__ == "__main__":
    # Se nenhum argumento foi passado, tenta selecionar arquivo
    if len(sys.argv) < 2:
        print("Nenhum arquivo de música especificado.")
        audio_path = select_audio_file()
        if not audio_path:
            print("Nenhum arquivo selecionado. Saindo.")
            sys.exit(1)
    else:
        audio_path = sys.argv[1]
    
    main(audio_path)
