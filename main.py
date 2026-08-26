import sys
import time
import os
import tkinter as tk
from tkinter import filedialog

import pygame

from audio.input import AudioInput
from audio.analyzer import AudioAnalyzer 
from memory.musical_memory import MusicalMemory 
from state.visual_state import VisualStateController
from geometry.shape import create_circle_shape
from geometry.deformation import deform_shape  
from renderer.renderer import Renderer 

# Extensões de áudio suportadas pelo soundfile (libsndfile)
AUDIO_EXTENSIONS = [
    ("Arquivos de Áudio", "*.wav *.flac *.ogg *.mp3 *.aiff *.aif *.au *.raw *.pcm"),
    ("Todos os arquivos", "*.*")
]

def select_audio_file(initial_dir: str = None) -> str | None:
    """Abre diálogo nativo do SO para selecionar arquivo de áudio."""
    # Tkinter precisa de uma root oculta
    root = tk.Tk()
    root.withdraw()  # Esconde a janela principal
    root.attributes('-topmost', True)  # Garante que o diálogo fique no topo
    
    try:
        file_path = filedialog.askopenfilename(
            title="Selecionar arquivo de áudio",
            initialdir=initial_dir or os.path.expanduser("~"),
            filetypes=AUDIO_EXTENSIONS
        )
        return file_path if file_path else None
    finally:
        root.destroy()

def reset_pipeline(audio_path: str):
    """Cria/inicializa todos os componentes do pipeline."""
    audio_input = AudioInput(audio_path)
    analyzer = AudioAnalyzer()
    memory = MusicalMemory()
    visual_controller = VisualStateController() 
    shape = create_circle_shape(vertex_count=72)
    
    audio_input.play()
    return audio_input, analyzer, memory, visual_controller, shape

def main(audio_path: str = None) -> None:
    # 1. Seleção de arquivo (CLI > Dialog)
    if not audio_path:
        audio_path = select_audio_file()
        if not audio_path:
            print("Nenhum arquivo selecionado. Saindo.")
            return

    if not os.path.exists(audio_path):
        print(f"Erro: O arquivo '{audio_path}' não existe.")
        return

    # 2. Inicialização
    renderer = Renderer()
    audio_input, analyzer, memory, visual_controller, shape = reset_pipeline(audio_path)
    
    start_time = time.time()
    last_time = start_time 
    latest_features = None
    latest_context = None 
    running = True 
    last_dir = os.path.dirname(audio_path)
    audio_warning_shown = False

    while running:
        # 3. Eventos (Renderer retorna lista de eventos pygame)
        events = renderer.handle_events()
        if events is False:  # Sinal de quit do renderer (headless mode fallback)
            running = False
            continue
            
        # Processa teclas de atalho
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_o:  # Tecla 'O' para abrir novo arquivo
                    new_path = select_audio_file(initial_dir=last_dir)
                    if new_path:
                        last_dir = os.path.dirname(new_path)
                        # Reinicializa pipeline completo
                        audio_input, analyzer, memory, visual_controller, shape = reset_pipeline(new_path)
                        start_time = time.time()
                        last_time = start_time
                        latest_features = None
                        latest_context = None
                        audio_warning_shown = False

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

        debug_lines = _build_debug_lines(latest_features, latest_context, visual_state, audio_path, audio_input)
        renderer.draw(vertices, debug_lines)

        # Mostra aviso visual se audio nao esta tocando mas visuals estao ativos
        if not audio_warning_shown and not audio_input._mixer_available and latest_features is not None:
            print("[AVISO] Audio offline: visuals reagem mas sem som. Verifique pygame.mixer.")
            audio_warning_shown = True

        if audio_input.is_finished():
            # Auto-loop ou parar? Vamos parar por enquanto.
            running = False

    renderer.quit()

def _build_debug_lines(features, context, visual_state, current_file, audio_input) -> list:
    lines = [
        "VISUALIZADOR DE MUSICA COM MEMORIA CONTEXTUAL",
        f"Arquivo: {os.path.basename(current_file)}",
        "Controles: [O] Abrir arquivo | [ESC] Sair"
    ]
    
    # Indicador de status de audio
    audio_status = "ONLINE" if audio_input._mixer_available else "OFFLINE (sem som)"
    lines.append(f"Audio: {audio_status}")
    
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
    cli_path = sys.argv[1] if len(sys.argv) > 1 else None
    main(cli_path)
