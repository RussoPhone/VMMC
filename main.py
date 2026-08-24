import sys
import time
import os

# Adicionando suporte ao Dolphin
try:
    import dolphin
    DOLPHIN_AVAILABLE = True
except ImportError:
    DOLPHIN_AVAILABLE = False

from audio.input import AudioInput
from audio.analyzer import AudioAnalyzer 
from memory.musical_memory import MusicalMemory 
from state.visual_state import VisualStateController
from geometry.shape import create_circle_shape
from geometry.deformation import deform_shape  
from renderer.renderer import Renderer 

def select_audio_file_with_dolphin() -> str:
    """Solicita seleção de arquivo de música com integração ao Dolphin."""
    if DOLPHIN_AVAILABLE:
        try:
            # Tenta usar o Dolphin para seleção de arquivo
            file_path = dolphin.select_file(
                title="Selecione um arquivo de música",
                filters=[("Arquivos de áudio", "*.mp3 *.wav *.flac *.ogg")]
            )
            if file_path:
                return file_path
        except Exception as e:
            print(f"[AVISO] Falha ao usar Dolphin: {e}")
            # Se Dolphin falhar, cai para seleção manual
            pass
    
    # Fallback para seleção manual
    try:
        print("Selecione um arquivo de música:")
        file_path = input().strip()
        return file_path
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao selecionar arquivo: {e}")
        sys.exit(1)

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
    # Abre imediatamente o Dolphin para seleção do arquivo de música
    if not DOLPHIN_AVAILABLE:
        print("Dolphin não disponível. Usando seleção manual.")
        audio_path = select_audio_file_with_dolphin()
    else:
        audio_path = select_audio_file_with_dolphin()
    
    # Verifica se um arquivo foi selecionado
    if not audio_path:
        print("Nenhum arquivo selecionado. Saindo.")
        sys.exit(1)
    
    main(audio_path)
