import sys
import time
import os
from pathlib import Path

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

def select_audio_folder_with_dolphin() -> str:
    """Solicita seleção de pasta com integração ao Dolphin e retorna o primeiro arquivo de áudio encontrado."""
    if DOLPHIN_AVAILABLE:
        try:
            # Tenta usar o Dolphin para seleção de pasta
            folder_path = dolphin.select_folder(
                title="Selecione uma pasta com arquivos de música"
            )
            if folder_path:
                # Verifica se o caminho é válido
                if not os.path.exists(folder_path):
                    print(f"Erro: O caminho '{folder_path}' não existe.")
                    return None
                    
                if not os.path.isdir(folder_path):
                    print(f"Erro: '{folder_path}' não é um diretório válido.")
                    return None
                
                # Procura por arquivos de áudio na pasta
                audio_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}
                folder = Path(folder_path)
                
                # Encontra o primeiro arquivo de áudio compatível
                for file in folder.iterdir():
                    if file.is_file() and file.suffix.lower() in audio_extensions:
                        return str(file)
                        
                print("Nenhum arquivo de áudio encontrado na pasta selecionada.")
                return None
        except Exception as e:
            print(f"[AVISO] Falha ao usar Dolphin: {e}")
            # Se Dolphin falhar, cai para seleção manual
            pass
    
    # Fallback para seleção manual de pasta
    try:
        print("Selecione uma pasta com arquivos de música:")
        print("Exemplos de caminhos válidos:")
        print("- Windows: C:\\Users\\SeuNome\\Music")
        print("- Linux/Mac: /home/seunome/Música ou /Users/seunome/Music")
        folder_path = input().strip()
        
        # Verifica se o caminho é válido
        if not os.path.exists(folder_path):
            print(f"Erro: O caminho '{folder_path}' não existe.")
            return None
            
        if not os.path.isdir(folder_path):
            print(f"Erro: '{folder_path}' não é um diretório válido.")
            return None
            
        # Procura por arquivos de áudio na pasta
        audio_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}
        folder = Path(folder_path)
        
        # Encontra o primeiro arquivo de áudio compatível
        for file in folder.iterdir():
            if file.is_file() and file.suffix.lower() in audio_extensions:
                return str(file)
                
        print("Nenhum arquivo de áudio encontrado na pasta selecionada.")
        return None
        
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao selecionar pasta: {e}")
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
    # Abre imediatamente o Dolphin para seleção da pasta
    audio_path = select_audio_folder_with_dolphin()
    
    # Verifica se um arquivo foi selecionado
    if not audio_path:
        print("Nenhum arquivo selecionado. Saindo.")
        sys.exit(1)
    
    main(audio_path)
