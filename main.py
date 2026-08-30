import os
import sys
import time
import tkinter as tk
from tkinter import filedialog

import pygame

from audio.analyzer import AudioAnalyzer
from audio.input import AudioInput, AudioPlaybackError, PlaybackState
from geometry.deformation import deform_shape
from geometry.shape import create_circle_shape
from memory.musical_memory import MusicalMemory
from renderer.renderer import Renderer
from state.visual_state import VisualStateController


AUDIO_EXTENSIONS = [
    ("Arquivos de Áudio", "*.wav *.flac *.ogg *.mp3 *.aiff *.aif *.au *.raw *.pcm"),
    ("Todos os arquivos", "*.*"),
]


def select_audio_file(initial_dir: str = None) -> str | None:
    """Open the native file dialog and return the selected audio path."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    try:
        file_path = filedialog.askopenfilename(
            title="Selecionar arquivo de áudio",
            initialdir=initial_dir or os.path.expanduser("~"),
            filetypes=AUDIO_EXTENSIONS,
        )
        return file_path if file_path else None
    finally:
        root.destroy()


def drain_audio_frames(audio_input, analyzer, memory):
    """Analyze every audio frame that elapsed since the previous draw."""
    latest_features = None
    latest_context = None
    while (frame := audio_input.get_next_frame()) is not None:
        latest_features = analyzer.analyze(frame)
        latest_context = memory.update(latest_features)
    return latest_features, latest_context


def reset_pipeline(audio_path: str, previous_audio=None):
    """Create a fresh pipeline after stopping any previous output stream."""
    if previous_audio is not None:
        previous_audio.stop()

    audio_input = AudioInput(audio_path)
    analyzer = AudioAnalyzer()
    memory = MusicalMemory()
    visual_controller = VisualStateController()
    shape = create_circle_shape(vertex_count=72)
    audio_input.play()
    return audio_input, analyzer, memory, visual_controller, shape


def main(audio_path: str = None) -> None:
    if not audio_path:
        audio_path = select_audio_file()
        if not audio_path:
            print("Nenhum arquivo selecionado. Saindo.")
            return

    if not os.path.exists(audio_path):
        print(f"Erro: O arquivo '{audio_path}' não existe.")
        return

    renderer = None
    audio_input = None
    try:
        renderer = Renderer()
        audio_input, analyzer, memory, visual_controller, shape = reset_pipeline(audio_path)

        start_time = time.time()
        last_time = start_time
        latest_features = None
        latest_context = None
        running = True
        last_dir = os.path.dirname(audio_path)

        while running:
            events = renderer.handle_events()
            if events is False:
                break
            if events is True:
                events = []

            for event in events:
                if event.type != pygame.KEYDOWN:
                    continue
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_o:
                    new_path = select_audio_file(initial_dir=last_dir)
                    if new_path:
                        last_dir = os.path.dirname(new_path)
                        (
                            audio_input,
                            analyzer,
                            memory,
                            visual_controller,
                            shape,
                        ) = reset_pipeline(new_path, audio_input)
                        audio_path = new_path
                        start_time = time.time()
                        last_time = start_time
                        latest_features = None
                        latest_context = None

            now = time.time()
            dt = now - last_time
            last_time = now

            new_features, new_context = drain_audio_frames(
                audio_input,
                analyzer,
                memory,
            )
            if new_features is not None:
                latest_features = new_features
                latest_context = new_context

            if latest_context is not None:
                visual_state = visual_controller.update(latest_context, dt)
            else:
                visual_state = visual_controller.state

            vertices = deform_shape(shape, visual_state, now - start_time)
            debug_lines = _build_debug_lines(
                latest_features,
                latest_context,
                visual_state,
                audio_path,
                audio_input,
            )
            renderer.draw(vertices, debug_lines)

            if audio_input.is_finished():
                running = False
    except AudioPlaybackError as exc:
        print(f"[ERRO] {exc}")
        print("Verifique o dispositivo padrão com 'pactl info' e 'python -m sounddevice'.")
    finally:
        if audio_input is not None:
            audio_input.stop()
        if renderer is not None:
            renderer.quit()


def _build_debug_lines(features, context, visual_state, current_file, audio_input) -> list:
    lines = [
        "VISUALIZADOR DE MUSICA COM MEMORIA CONTEXTUAL",
        f"Arquivo: {os.path.basename(current_file)}",
        "Controles: [O] Abrir arquivo | [ESC] Sair",
    ]

    status_labels = {
        PlaybackState.STOPPED: "PARADO",
        PlaybackState.PLAYING: "REPRODUZINDO",
        PlaybackState.FINISHED: "FINALIZADO",
        PlaybackState.FAILED: "ERRO",
    }
    lines.append(f"Audio: {status_labels[audio_input.state]}")

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


def cli() -> None:
    audio_path = sys.argv[1] if len(sys.argv) > 1 else None
    main(audio_path)


if __name__ == "__main__":
    cli()
