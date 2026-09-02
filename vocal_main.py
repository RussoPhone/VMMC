"""Voice-only experimental entry point for VMMC."""

import os
import sys
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog

import pygame

from audio.analyzer import AudioAnalyzer
from audio.input import AudioInput, AudioPlaybackError
from audio.live_input import SystemAudioInput
from expression.vocal_gate import VocalGate
from memory.musical_memory import MusicalMemory
from renderer.vocal_renderer import VocalRenderer


SYSTEM_AUDIO_FLAG = "--system-audio"
AUDIO_EXTENSIONS = [
    ("Arquivos de Áudio", "*.wav *.flac *.ogg *.mp3 *.aiff *.aif *.au *.raw *.pcm"),
    ("Todos os arquivos", "*.*"),
]


@dataclass(frozen=True)
class VocalFrame:
    audio_frame: object
    features: object
    context: object
    gate: object


def drain_vocal_frames(
    audio_input,
    analyzer,
    memory,
    gate,
    previous_timestamp=None,
):
    latest = None
    last_timestamp = previous_timestamp
    while (audio_frame := audio_input.get_next_frame()) is not None:
        features = analyzer.analyze(audio_frame)
        dt = (
            1.0 / 30.0
            if last_timestamp is None
            else max(0.0, min(0.1, features.timestamp - last_timestamp))
        )
        last_timestamp = features.timestamp
        context = memory.update(features)
        gate_state = gate.update(features, context, dt)
        latest = VocalFrame(audio_frame, features, context, gate_state)
    return latest


def create_audio_input(source):
    return SystemAudioInput() if source == SYSTEM_AUDIO_FLAG else AudioInput(source)


def select_audio_file(initial_dir=None):
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askopenfilename(
            title="Selecionar áudio para o laboratório vocal",
            initialdir=initial_dir or os.path.expanduser("~"),
            filetypes=AUDIO_EXTENSIONS,
        )
        return selected or None
    finally:
        root.destroy()


def reset_pipeline(source, previous_audio=None):
    if previous_audio is not None:
        previous_audio.stop()
    audio = create_audio_input(source)
    analyzer = AudioAnalyzer()
    memory = MusicalMemory()
    gate = VocalGate()
    audio.play()
    return audio, analyzer, memory, gate


def cli():
    source = sys.argv[1] if len(sys.argv) > 1 else None
    main(source)


def main(source=None):
    if not source:
        source = select_audio_file()
        if not source:
            return
    if source != SYSTEM_AUDIO_FLAG and not os.path.exists(source):
        print(f"Erro: O arquivo '{source}' não existe.")
        return

    renderer = None
    audio = None
    try:
        renderer = VocalRenderer()
        audio, analyzer, memory, gate = reset_pipeline(source)
        latest = None
        previous_timestamp = None
        last_dir = os.path.dirname(source)
        running = True
        while running:
            for event in renderer.handle_events():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_o:
                    selected = select_audio_file(last_dir)
                    if selected:
                        last_dir = os.path.dirname(selected)
                        audio, analyzer, memory, gate = reset_pipeline(selected, audio)
                        source = selected
                        latest = None
                        previous_timestamp = None
            new_frame = drain_vocal_frames(
                audio,
                analyzer,
                memory,
                gate,
                previous_timestamp,
            )
            if new_frame is not None:
                latest = new_frame
                previous_timestamp = latest.features.timestamp
            renderer.draw(latest, record=new_frame is not None)
            if audio.is_finished():
                running = False
    except AudioPlaybackError as exc:
        print(f"[ERRO] {exc}")
    finally:
        if audio is not None:
            audio.stop()
        if renderer is not None:
            renderer.quit()


if __name__ == "__main__":
    cli()
